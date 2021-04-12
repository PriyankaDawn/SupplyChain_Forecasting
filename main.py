# -*- coding: utf-8 -*-
"""
Created on Sun Apr 11 15:12:50 2021

@author: Priyanka.Dawn
testing
"""


#Importing required libraries
import pandas as pd
import numpy as np
import os
import datetime
from datetime import datetime
# from isoweek import Week
import matplotlib as plt
import seaborn as sns

import statsmodels.api as sm
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf,plot_pacf
from statsmodels.tsa.arima_model import ARIMA
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
# import xgboost
from sklearn.metrics import mean_squared_error, mean_absolute_error
from pmdarima.arima import auto_arima

import warnings
warnings.filterwarnings("ignore")

#File path
# os.chdir('C:\\Users\\priyanka.dawn\\OneDrive - EY\\Documents\\PD\\Kaggle')
os.chdir('D:\\PyCharm_Projects\\forecasting_v1')

# data_path = './Sample data'
data_path = './Data'


## Module 1 - Collating all data files and data understanding - variable definition
## Module 2 - Data cleaning and EDA - Boxplot - Correlation
## Module 3 - Feature engineering
## Module 4 - Model Building
## Module 5 - Output with KPI 

# Module 1 - Data Preparation
#============================
#Reading input files  
Sales_weekly=pd.read_csv(os.path.join(data_path,"Sales_sample.csv"))
Promo_weekly = pd.read_csv(os.path.join(data_path,"Promo_sample.csv"))
Season_data= pd.read_csv(os.path.join(data_path,"Season_sample.csv"))


def sales_prep(sales_input):
    #Change column names and date format
    sales_input=sales_input.sort_values(['SKU', 'ISO_week'])
    
    #Maintaining continuity in data
    SKU = sales_input["SKU"].unique()
    all_weeks = list(sales_input["ISO_week"].unique())
    sales_continuous = pd.MultiIndex.from_product([SKU,all_weeks], names = ["SKU", "ISO_week"])
    sales_continuous = pd.DataFrame(index = sales_continuous).reset_index()
    sales_continuous = sales_continuous.merge(sales_input,how='left',on=['SKU','ISO_week'])
    sales_continuous["Sales"].fillna(0,inplace=True)
    #Initial zero removal for sales 
    sales_initial=sales_continuous.sort_values(['SKU','ISO_week'],ascending=True).reset_index(drop=True)
    sales_initial.set_index(['SKU', 'ISO_week'], inplace = True)
    sales_zeroSearch = (sales_initial['Sales'] != 0).groupby(level=0).cumsum()
    sales_treated = sales_initial[sales_zeroSearch != 0].reset_index() 
    sales_treated=sales_treated.reset_index(drop = True)
    sales_treated.sort_values(['SKU','ISO_week'])
    return sales_treated

sales_processed=sales_prep(Sales_weekly)

def merge_df(sales_data,promo_data,season):
    promo_data.rename(columns={'EAN':'SKU'},inplace=True)
    promo_data=promo_data.drop_duplicates()
    merged_data=sales_data.merge(promo_data,how='left',on=['SKU','ISO_week'])
    merged_data=merged_data.merge(Season_data,how='left',on=['ISO_week'])
    merged_data.loc[merged_data['Promo_flag'].isnull(),'Promo_flag']=0
    return merged_data
    
merged_data=merge_df(sales_processed,Promo_weekly,Season_data)
    


##subsetting the merged data for one SKU

merged_data=merged_data[merged_data['SKU']==10305]

# Module 2 - Data cleaning and EDA

# Total Sales per week
weekly_sales = pd.DataFrame(merged_data.groupby(['ISO_week'])['Sales'].sum())
ax = weekly_sales.unstack().plot(kind='line')

ax.set_xticklabels(weekly_sales.index)
ax.set_xlabel('ISO_week')

ax.set_ylabel('Sales')

#Missing data - Need to add promo and holiday

# Box plots
'''n=10
sku_sales= pd.DataFrame(merged_data.groupby(['SKU'])['Sales'].sum())
sku_topn =sku_sales.sort_values(['Sales'],ascending = False)['SKU'].unique()[0:n]
sku_sales_top=sku_sales[sku_sales['SKU'].isin(sku_topn)]'''

for sku, sku_df in merged_data.groupby(['SKU']):
    ax = sku_df.boxplot(by='SEASON',column='Sales', grid=False)
    ax.set_title('Season for {}'.format(sku))
    
#Outlier treatment
def outlier_mean3sd(df,column_name):
    upper_level=df[column_name].mean()+3*df[column_name].std()
    lower_level=df[column_name].mean()-3*df[column_name].std()
    df['sales_treated']=np.where(df[column_name]>upper_level,upper_level,df[column_name])
    df['sales_treated']=np.where(df[column_name]<lower_level,lower_level,df['sales_treated'])
    del df[column_name]
    df.rename(columns={'sales_treated':column_name},inplace=True)
    return(df)

def outlier_mean2sd(df,column_name):
    upper_level=df[column_name].mean()+2*df[column_name].std()
    lower_level=df[column_name].mean()-2*df[column_name].std()
    df['sales_treated']=np.where(df[column_name]>upper_level,upper_level,df[column_name])
    df['sales_treated']=np.where(df[column_name]<lower_level,lower_level,df['sales_treated'])
    del df[column_name]
    df.rename(columns={'sales_treated':column_name},inplace=True)
    return(df)

treated_data_3sd = outlier_mean3sd(merged_data,'Sales')

## Module 3 - Feature engineering - Not many features right now- Promo flag ans season
df_new=merged_data.copy(deep=True)


# Test for stationarity
def adf_check(time_series,sku,lag):
    """
    Pass in a time series, returns ADF report
    """
    result = adfuller(time_series)
    print('Augmented Dickey-Fuller Test for SKU - {} for {} :'.format(sku,lag))
    labels = ['ADF Test Statistic','p-value','#Lags Used','Number of Observations Used']

    for value,label in zip(result,labels):
        print(label+' : '+str(value) )
    
    if result[1] <= 0.05:
        print("strong evidence against the null hypothesis, reject the null hypothesis. Data has no unit root and is stationary")
    else:
        print("weak evidence against null hypothesis, time series has a unit root, indicating it is non-stationary ")


for sku,sku_df in df_new.groupby(['SKU']): # Change this as per promo
    sku_df.set_index(['ISO_week'], inplace=True)
    sku_df.drop(['SKU','Promo_flag'], axis=1, inplace=True)
    
    print("ADF checks for {}\n\n".format(sku))
    sku_df['Sales Weekly Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(1)
    print(adf_check(sku_df['Sales Weekly Difference'].dropna(),sku,"Weekly Difference"))
    
    sku_df['Sales Monthly Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(4)
    print(adf_check(sku_df['Sales Monthly Difference'].dropna(),sku,"Monthly Difference"))
    
    sku_df['Sales Seasonal Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(13)
    print(adf_check(sku_df['Sales Seasonal Difference'].dropna(),sku,"Seasonal Difference"))
    

# Autocorrelation Plots
for sku,sku_df in df_new.groupby(['SKU']):
    sku_df_main = sku_df.copy()
    sku_df.set_index(['ISO_week'], inplace=True)
    sku_df.drop(['SKU','SEASON','Promo_flag'], axis=1, inplace=True)
    
    sku_df['Sales Weekly Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(1)
    fig1 = plot_acf(sku_df['Sales Weekly Difference'].dropna())
    fig1.suptitle("Sales Weekly Difference ACF plot for - {}".format(sku))
    
    sku_df['Sales Monthly Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(4)
    fig2 = plot_acf(sku_df['Sales Monthly Difference'].dropna())
    fig2.suptitle("Sales Monthly Difference ACF plot for - {}".format(sku))
    
    sku_df['Sales Seasonal Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(13)
    fig3 = plot_acf(sku_df['Sales Seasonal Difference'].dropna())
    fig3.suptitle("Sales Seasonal Difference ACF plot for - {}".format(sku))
    
# Partial - Autocorrelation Plots
for sku,sku_df in df_new.groupby(['SKU']):
    sku_df.set_index(['ISO_week'], inplace=True)
    sku_df.drop(['SKU','SEASON','Promo_flag'], axis=1, inplace=True)
    
    sku_df['Sales Weekly Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(1)
    fig1 = plot_pacf(sku_df['Sales Weekly Difference'].dropna())
    fig1.suptitle("Sales Weekly Difference PACF plot for - {}".format(sku))
    
    sku_df['Sales Monthly Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(4)
    fig2 = plot_pacf(sku_df['Sales Monthly Difference'].dropna())
    fig2.suptitle("Sales Monthly Difference PACF plot for - {}".format(sku))
    
    sku_df['Sales Seasonal Difference'] = sku_df['Sales'] - sku_df['Sales'].shift(13)
    fig3 = plot_pacf(sku_df['Sales Seasonal Difference'].dropna())
    fig3.suptitle("Sales Seasonal Difference PACF plot for - {}".format(sku))
    
sku_df=df_new.groupby(['SKU'])['Sales'].sum().reset_index()

# EWMA on using different spans
for sku,sku_df in df_new.groupby(['SKU']):
    #sku_df.set_index(['ISO_week'], inplace=True)
    #sku_df.drop(['SKU','ISO_Week'], axis=1, inplace=True)
    sku_df['EWMA_2_weeks'] = sku_df['Sales'].ewm(span=2).mean()
    sku_df['EWMA_4_weeks'] = sku_df['Sales'].ewm(span=4).mean()
    sku_df['EWMA_8_weeks'] = sku_df['Sales'].ewm(span=8).mean()
    sku_df['EWMA_13_weeks'] = sku_df['Sales'].ewm(span=8).mean()
    ax = sku_df[['Sales','EWMA_2_weeks','EWMA_4_weeks','EWMA_8_weeks','EWMA_13_weeks']].plot()
    ax.set_title('EWMA Sales plot for - {}'.format(sku))

## Module 4 - Model Building
#Random Forest regressor


def execute_random_forest(training_data,testing_data,lag_cols):
    col_names = list(training_data.columns)
    excluded_features= ['SKU','Sales','ISO_week']
    lag_cols=list(lag_cols)
    excluded_features=excluded_features + lag_cols
    feature_list=list(set(col_names)-set(excluded_features))
    testing_data1=testing_data[feature_list]
    training_data1=training_data[feature_list]
    x_train=training_data1
    y_train = training_data.loc[:,"Sales"]
    rf = RandomForestRegressor(bootstrap=True, criterion='mse', #criterion='mse'
            max_depth=5, max_features='sqrt', max_leaf_nodes=None,
            min_impurity_split=None, min_samples_leaf=2,
            min_samples_split=4, min_weight_fraction_leaf=0.0, # min_samples_split=2
            n_estimators=300, n_jobs=2, oob_score=False, random_state=0, # n_estimators=300
            verbose=0, warm_start=False)
    rf.fit(x_train, y_train)
    y_test_predicted=rf.predict(testing_data1)
    #training_data['Predicted_rf']=y_train_predicted
    testing_data['Predicted_rf']=y_test_predicted.round(2)
    testing_data['Predicted_rf']=np.where(testing_data['Predicted_rf']<0,0,testing_data['Predicted_rf']) 
    result = testing_data[['Predicted_rf']]
    return result

def random_forest_importance_matrix(X):    
    #X = training_data
    X = X[X.columns.drop(list(X.filter(regex='Lag_')))]
    feature_list = list(X.columns)
    feature_list.remove("Actuals")
    features = np.array(X.drop(['Actuals'], axis = 1))
    target = np.array(X['Actuals'])
    rf = RandomForestRegressor(bootstrap=True, criterion='mse',
            max_depth=5, max_features='auto', max_leaf_nodes=None,
            min_impurity_split=None, min_samples_leaf=2,
            min_samples_split=2, min_weight_fraction_leaf=0.0,
            n_estimators=200, n_jobs=2, oob_score=False, random_state=0, ##400 or 300, depth
            verbose=0, warm_start=False)
    
    rf.fit(features, target)
    
    # Get numerical feature importances
    importances = list(rf.feature_importances_)
    # List of tuples with variable and importance
    feature_importances = [(feature, round(importance, 2)) for feature, importance in zip(feature_list, importances)]
    # Sort the feature importances by most important first
    feature_importances = sorted(feature_importances, key = lambda x: x[1], reverse = True)
    df = pd.DataFrame(feature_importances, columns =['Variable', 'Importance']) 
    return(df)


#Define test and train
def test_train_split(df,x):
    points = np.round(len(df['Sales'])*(x)/100).astype(int) 
    train_data = df.loc[:points]
    test_data = df.loc[points:]
    return train_data,test_data

#train_df,test_df=test_train_split(df_new,x=70)


Final_fcast=pd.DataFrame()
#Running random forest regressor for each SKU
for Sku in df_new['SKU'].unique():
    df_subset=df_new[df_new['SKU']==Sku]
    # Seasonal dummies
    dt_dummy=df_subset[['SEASON']]
    if(dt_dummy.shape[0]>0):
      dt_fit_dummy=pd.DataFrame()    
      dt_fit_dummy=pd.get_dummies(dt_dummy,drop_first=True)
    dt_fit_dummy['ISO_week']=df_subset['ISO_week']
    df_season=dt_fit_dummy
    
    # Adding it to merged data
    
    df_subset=df_subset.merge(df_season,how='left',on='ISO_week')
    
    del df_subset['SEASON'] 
    
    for i in range(1,5):
      df_subset['Lag_'+str(i)]=df_subset.Sales.shift(i)        

    #For the lag columns fill -999
    df_subset=df_subset.fillna(-999)
    
    
    #the train , test and prediction df
    training_data=pd.DataFrame()
    testing_data=pd.DataFrame()
    predicted_lag4=pd.DataFrame()

    lag_columns = ([col for col in df_subset if col.startswith('Lag_')])
    
    train_df,test_df=test_train_split(df_subset,x=70)
    result_rf = pd.DataFrame()

    result_rf =execute_random_forest(train_df,test_df,lag_columns)
    forecst_weeks=test_df['ISO_week'].unique()
    result_rf['Weeks']=forecst_weeks
    #result_xgb['Shipment_week']=fcast_weeks
    #rf_xgb=result_rf.merge(result_xgb,how="left",on="Shipment_week")
    Predicted_df=pd.DataFrame()
    Predicted_df=Predicted_df.append(result_rf)
    Predicted_df['SKU']=Sku
    Final_fcast=Final_fcast.append(Predicted_df) 
 



   
##Edit here onwards
'''feature_importance=random_forest_importance_matrix(training_data.copy(deep=True))
    feature_importance_dev=feature_importance.sort_values('Importance', ascending= False).iloc[:15,]
    feature_importance_dev['Key']= fu
    feature_importance_dev['Snapshot_Week']= fcast_weeks[0]
    feature_importance_dev = feature_importance_dev.pivot(index=['Key','Snapshot_Week'], columns='Variable',values='Importance').reset_index() '''   
    

#Xgb regressor
def execute_xgboost(training_data,testing_data):

    col_names = list(training_data.columns)
    excluded_features= ['SKU','Sales','ISO_week']
    
    feature_list=list(set(col_names)-set(excluded_features))
    testing_data1=testing_data[feature_list]
    training_data1=training_data[feature_list]
    x_train=training_data1
    y_train = training_data.loc[:,"Sales"]

    #x_train,x_test,y_train,y_test=train_test_split(training_data[feature_list],y_train,test_size=0.2,random_state = 0)
    #data_dmatrix = xgb.DMatrix(data=x_train,label=y_train)
    import xgboost as xgb
    #xg_reg = xgb.XGBRegressor(objective ='reg:squarederror', colsample_bytree = 0.3, learning_rate = 0.1,
     #           max_depth = 5,subsample=0.6,verbose=0,seed=123,reg_lambda=0.45,reg_alpha=0.75,gamma=0, n_estimators = 10, min_child_weight=1.5)
    xg_reg=xgb.XGBRegressor(objective ='reg:squarederror',missing=-999,seed=123)
    xg_reg.fit(x_train, y_train)

    #preds = xg_reg.predict(testing_data1)#
    #rf.fit(x_train, y_train)

    #y_train_predicted=xg_reg.predict(training_data1)
    y_test_predicted=xg_reg.predict(testing_data1)
    
    #training_data['Predicted_xgb']=y_train_predicted
    testing_data['Predicted_xgb']=y_test_predicted.round(2)
    testing_data['Predicted_xgb']=np.where(testing_data['Predicted_xgb']<0,0,testing_data['Predicted_xgb'])
    
       
    result = testing_data[['Predicted_xgb']]

    return result



# Additional univariate models
'''def run_fcast(ser,model,h,period):
    if model == "arima":
        print("Running Arima.........")
        stepwise_model_arima = auto_arima(ser, start_p=0, start_q=0,max_p=2, max_q=2, m=period,seasonal=False,max_d=1,
                           trace=False,
                           error_action='ignore',  
                           suppress_warnings=True, 
                           stepwise=True)
        fcast = np.round(stepwise_model_arima.predict(n_periods=h)).astype(int)
        fcast[fcast<0] = 0
        return fcast;

    elif model == "ma":
        print("Running Moving Average...........")
        fcast_12 = float(ser.rolling(12).mean().iloc[-1])
        fcast_8 = float(ser.rolling(8).mean().iloc[-1])
        fcast_4 = float(ser.rolling(4).mean().iloc[-1])
        fcast_1 = float(ser.rolling(1).mean().iloc[-1])
        fcast = np.round([statistics.mean([fcast_12,fcast_8,fcast_4,fcast_1])]*h).astype(int)
        fcast[fcast<0] = 0
        return fcast;
    elif model == "simexp":
        print("Running Simple Exp..............")
        fcast = np.round(SimpleExpSmoothing(np.asarray(ser)).fit(smoothing_level=0.4,optimized=False).forecast(h)).astype(int)
        fcast[fcast<0] = 0
        return fcast;
    elif model == "holtlinear":
        print("Running Holt Linear............")
        fcast = np.round(Holt(ser).fit(smoothing_level = 0.3,smoothing_slope = 0.1).forecast(h)).astype(int)
        fcast[fcast<0] = 0
        return fcast;
    elif model == "holtwinter":
        print("Running Holt Winters...........")
        fcast = np.round(ExponentialSmoothing(ser ,seasonal_periods=52 ,trend='add', 
                                seasonal='add').fit(optimized = True).forecast(h)).astype(int)
        fcast[fcast<0] = 0
        return fcast;
    elif model == "ucm":
        print("Running UCM.........")
        model = sm.tsa.UnobservedComponents(ser, level = True, cycle=True, stochastic_cycle=True,seasonal = 52)
        pred_uc = list(model.fit().get_forecast(steps = h).predicted_mean)
        fcast = [int(round(x)) for x in pred_uc]
        pred = [0 if i < 0 else i for i in fcast]

        #fcast = fcast.astype(int)
        return pred;  
    elif model == "croston":
        print("Running Croston.........")
        pred_cros = Croston(ser,h,0.4)
        pred_cros = pred_cros[pred_cros['Demand'].isnull()]['Forecast']
        fcast = round(pred_cros).astype(int)
        fcast[fcast<0] = 0
        return fcast;  
    elif model == "naive_seasonal":
        print("Running Naive Seasonal......")
        if len(ser)>period:
            fcast = round(ser[-52:][:h]).astype(int)
            fcast[fcast<0] = 0
            return fcast;
    else:
            fcast = np.repeat(np.nan,h)
            return fcast;

    if model == "arima":
        print("Running Arima.........")
        stepwise_model_arima = auto_arima(ser, start_p=0, start_q=0,max_p=2, max_q=2, m=period,seasonal=False,max_d=1,
                           trace=False,
                           error_action='ignore',  
                           suppress_warnings=True, 
                           stepwise=True)
        fcast = np.round(stepwise_model_arima.predict(n_periods=h)).astype(int)
        fcast[fcast<0] = 0
        return fcast'''