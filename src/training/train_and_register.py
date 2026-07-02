import pandas as pd
import numpy as np
import mlflow
import mlflow.pyfunc
from xgboost import XGBClassifier, XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import create_engine
import os

mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow_container:5001"))
os.environ["MLFLOW_ARTIFACT_UPLOAD_DOWNLOAD_TIMEOUT"] = "300"
mlflow.set_experiment("2Stage_Fishing_Production")

HORIZONS = list(range(1, 8))
FEATURES  = [
    'lat_grid', 'lon_grid', 'fishing_hours', 'geartype',
    'month', 'sst', 'salinity', 'current_u', 'current_v',
    'wave_height_max', 'wave_period_max', 'wind_speed_max', 'wind_dir',
    'lag_1', 'lag_2', 'lag_3', 'lag_7', 'lag_14', 'lag_365',
    'rolling_mean_7', 'rolling_std_7', 'rolling_max_7',
    'rolling_mean_14', 'rolling_std_14', 'rolling_max_14',
]

BEST_PARAMS_CLF = {
    'n_estimators' : 1200,
    'max_depth' : 12,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'tree_method' : 'hist',
    'enable_categorical': True,
}

BEST_PARAMS_REG = {
    'n_estimators' : 1700,
    'max_depth': 13,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'tree_method': 'hist',
}

THRESHOLDS = {1: 0.55, 2: 0.50, 3: 0.48, 4: 0.45, 5: 0.45, 6: 0.43, 7: 0.40}


class TwoStageModel(mlflow.pyfunc.PythonModel):

    def __init__(self, clf, reg, threshold, calib_scale, features):
        self.clf= clf
        self.reg= reg
        self.threshold = threshold
        self.calib_scale = calib_scale
        self.features = features

    def predict(self, context, model_input):
        import numpy as np
        X = model_input[self.features].values
        proba = self.clf.predict_proba(X)[:, 1]
        is_active = (proba > self.threshold).astype(int)
        y_pred= np.zeros(len(X))
        active = is_active == 1
        if active.sum() > 0:
            y_pred[active] = self.reg.predict(X[active]) * self.calib_scale
        result = model_input[['lat_grid', 'lon_grid']].copy()
        result['prediction'] = y_pred
        result['is_active']  = is_active
        return result


def train_and_register():
    engine = create_engine("postgresql://db_user:db_password@db:5432/db")
    df = pd.read_sql_table("table_features", engine, schema="dev")
    df = df.sort_values("date").reset_index(drop=True)
    df['geartype'] = df['geartype'].astype('category')
    print(f"Loaded: {df.shape}")

    # splits
    N_CELLS     = df.groupby("date").size().iloc[0]
    N_TEST_DAYS = 180
    N_TEST_ROWS = N_TEST_DAYS * N_CELLS

    X_all = df[FEATURES]
    X_tr  = X_all.iloc[:-N_TEST_ROWS]
    X_te  = X_all.iloc[-N_TEST_ROWS:]

    # scale_pos_weight per horizon
    SPW = {}
    for H in HORIZONS:
        y_h = df[f'target_h{H}']
        ratio  = (y_h == 0).sum() / max((y_h > 0).sum(), 1)
        SPW[H] = round(ratio, 1)

    client = mlflow.tracking.MlflowClient()

    for H in HORIZONS:
        print(f"\n── Training J+{H} ──")
        y_h = df[f'target_h{H}']
        y_cls= (y_h > 0).astype(int)
        y_tr_cls = y_cls.iloc[:-N_TEST_ROWS]
        y_te_cls = y_cls.iloc[-N_TEST_ROWS:]
        y_tr_reg = y_h.iloc[:-N_TEST_ROWS]
        y_te_reg = y_h.iloc[-N_TEST_ROWS:]

        # stage 1 : classifier
        clf = XGBClassifier(**BEST_PARAMS_CLF, scale_pos_weight=SPW[H],
                            eval_metric='aucpr', verbosity=0)
        clf.fit(X_tr, y_tr_cls)

        y_pred_proba = clf.predict_proba(X_te)[:, 1]
        y_pred_cls   = (y_pred_proba > THRESHOLDS[H]).astype(int)

        # stage 2 : regressor with sample weights
        active_tr = y_tr_cls == 1
        sample_weights = np.log1p(y_tr_reg[active_tr].values)
        reg = XGBRegressor(**BEST_PARAMS_REG,
                           objective='reg:squarederror', verbosity=0)
        reg.fit(X_tr[active_tr], y_tr_reg[active_tr],
                sample_weight=sample_weights)

        # calibration
        y_pred_train = reg.predict(X_tr[active_tr])
        calib_scale = float(y_tr_reg[active_tr].mean() / y_pred_train.mean())

        # predictions
        y_pred = np.zeros(len(X_te))
        active_te = y_pred_cls == 1
        if active_te.sum() > 0:
            y_pred[active_te] = reg.predict(X_te[active_te]) * calib_scale

        # metrics
        mae_h = mean_absolute_error(y_te_reg, y_pred)
        rmse_h = np.sqrt(mean_squared_error(y_te_reg, y_pred))
        zero_m = (y_te_reg == 0)
        mad0_h = np.mean(np.abs(y_pred[zero_m.values])) if zero_m.any() else 0.0
        madp_h = np.mean(np.abs(y_te_reg[~zero_m].values
                                 - y_pred[~zero_m.values])) if (~zero_m).any() else 0.0

        active_mask = y_te_reg > 0
        reg_ratio = y_pred[active_mask.values].mean() / y_te_reg[active_mask].mean()
        clf_ratio = active_te.sum() / y_te_cls.sum()

        print(f"MAE={mae_h:.4f} | RMSE={rmse_h:.4f} | "
              f"MAD0={mad0_h:.4f} | MAD+={madp_h:.4f} | "
              f"ClfR={clf_ratio:.2f}x | RegR={reg_ratio:.2f}x")

        # register in MLflow Model Registry
        model_name = f"fishing_2stage_J{H}"
        wrapper = TwoStageModel(clf, reg, THRESHOLDS[H], calib_scale, FEATURES)

        with mlflow.start_run(run_name=f"2Stage_J+{H}_PROD"):
            mlflow.log_params({
                **BEST_PARAMS_CLF,
                'reg_n_estimators': BEST_PARAMS_REG['n_estimators'],
                'reg_max_depth': BEST_PARAMS_REG['max_depth'],
                'reg_learning_rate': BEST_PARAMS_REG['learning_rate'],
                'horizon': f'J+{H}',
                'threshold': THRESHOLDS[H],
                'calib_scale': round(calib_scale, 4),
                'scale_pos_weight': SPW[H],
                'model_type': '2stage_v4',
            })
            mlflow.log_metrics({
                'test_mae'  : mae_h,
                'test_rmse' : rmse_h,
                'test_mad0' : mad0_h,
                'test_madp' : madp_h,
                'clf_ratio' : clf_ratio,
                'reg_ratio' : reg_ratio,
            })

            mlflow.pyfunc.log_model(
                artifact_path=f"model_J+{H}",
                python_model=wrapper,
                registered_model_name=model_name,
            )

            versions = client.search_model_versions(
                filter_string=f"name='{model_name}'",
                order_by=["version_number DESC"],
                max_results=1,
            )
            if versions:
                client.set_registered_model_alias(
                    name=model_name,
                    alias="champion",
                    version=versions[0].version,
                )
                print(f"→ '{model_name}' v{versions[0].version} → champion")

    print("\nAll 7 models trained and registered.")


if __name__ == "__main__":
    train_and_register()