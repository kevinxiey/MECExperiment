import os
import warnings
import sys

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import ElasticNet

import pickle
import xgboost as xgb

import mlflow
import mlflow.sklearn


def eval_metrics(actual, pred):
    rmse = np.sqrt(mean_squared_error(actual, pred))
    mae = mean_absolute_error(actual, pred)
    r2 = r2_score(actual, pred)
    return rmse, mae, r2



if __name__ == "__main__":
    data = pd.read_csv('../data/weardatafeature.csv')

    train, test = train_test_split(data)

    # 转换成Dmatrix格式
    feature_columns = ['x_avg', 'y_avg', 'z_avg', 'vb_avg', 'x_stddev', 'y_stddev', 'z_stddev', 'vb_stddev', 'x_var',
                       'y_var', 'z_var', 'vb_var', 'x_rms', 'y_rms', 'z_rms', 'vb_rms']
    target_column = 'id'
    # 需要将dataframe格式的数据转化为矩阵形式
    xgtrain = xgb.DMatrix(train[feature_columns].values, train[target_column].values)
    xgtest = xgb.DMatrix(test[feature_columns].values, test[target_column].values)

    # 参数设定
    # param = {'max_depth':5, 'eta':0.1, 'silent':1, 'subsample':0.7, 'colsample_bytree':0.7, 'objective':'binary:logistic' }
    param = {
        'booster': 'gbtree',
        'objective': 'multi:softmax',  # 多分类的问题
        'num_class': 4,  # 类别数，与 multisoftmax 并用
        'gamma': 0.1,  # 用于控制是否后剪枝的参数,越大越保守，一般0.1、0.2这样子。
        'max_depth': 12,  # 构建树的深度，越大越容易过拟合
        'lambda': 2,  # 控制模型复杂度的权重值的L2正则化项参数，参数越大，模型越不容易过拟合。
        'subsample': 0.7,  # 随机采样训练样本
        'colsample_bytree': 0.7,  # 生成树时进行的列采样
        'min_child_weight': 3,
        'eta': 0.007,  # 如同学习率
        'seed': 1000,
        'nthread': 4,  # cpu 线程数
    }
    num_round = 10

    with mlflow.start_run():
        # 设定watchlist用于查看模型状态
        watchlist = [(xgtest, 'eval'), (xgtrain, 'train')]
        num_round = 10
        bst = xgb.train(param, xgtrain, num_round, watchlist)
        # 使用模型预测
        preds = bst.predict(xgtest)

        # 判断准确率
        labels = xgtest.get_label()
        print('error rate%f' % \
              (sum(1 for i in range(len(preds)) if preds[i] != labels[i]) / float(len(preds))))

        (rmse, mae, r2) = eval_metrics(labels, preds)

        print("  RMSE: %s" % rmse)
        print("  MAE: %s" % mae)
        print("  R2: %s" % r2)

        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2", r2)
        mlflow.log_metric("mae", mae)

        mlflow.xgboost.log_model(bst, "model")