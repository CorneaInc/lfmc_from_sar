# -*- coding: utf-8 -*-
"""
Created on Mon Sep 10 18:59:11 2018

@author: kkrao
"""
import os
import pandas as pd
import seaborn as sns
import numpy as np
import keras.backend as K
from dirs import dir_data, dir_codes, dir_figures
from fnn_smoothed_anomaly_all_sites import make_df, build_data, build_model,\
     infer_importance, plot_pred_actual, plot_importance,\
     decompose_plot_pred_actual, infer_importance_by_var_category
from keras.callbacks import ModelCheckpoint, LearningRateScheduler
from sklearn.metrics import mean_squared_error, r2_score

#%% 
def scheduler(epoch):
    lr_decay = 0.9
    if epoch%100 == 0:
        old_lr = K.get_value(model.optimizer.lr)
        new_lr = old_lr*lr_decay
        if new_lr<=1e-4:
            return  K.get_value(model.optimizer.lr)
        K.set_value(model.optimizer.lr, new_lr)
    return K.get_value(model.optimizer.lr)

# %%
####################################################################    ######
if __name__ == "__main__": 
    pd.set_option('display.max_columns', 30)
    
    ############################ inputs
    seed = 7
    np.random.seed(seed)
    epochs = int(5e3)
    retrain_epochs = int(1e3)
    batch_size = 2**12
    save_name = 'smoothed_all_sites_11_mar_2019_with_doy'
    load_model = True
    overwrite = False
    plot = 1
    response = "fm_smoothed"
#    dynamic_features = ["fm_anomaly","vv_anomaly","vh_anomaly",\
#                        "blue_anomaly","green_anomaly","red_anomaly","nir_anomaly",\
#                        'ndvi_anomaly', 'ndwi_anomaly',\
#                        'vv_ndvi_anomaly','vh_ndvi_anomaly',\
#                        'vv_red_anomaly','vh_red_anomaly',\
#                        'vv_nir_anomaly','vh_nir_anomaly',\
#                        'vv_blue_anomaly','vh_blue_anomaly',\
#                        'vv_green_anomaly','vh_green_anomaly']
    ## only opt
    #dynamic_features = ["fm_anomaly",\
    #                    "blue_anomaly","green_anomaly","red_anomaly","nir_anomaly",\
    #                    'ndvi_anomaly', 'ndwi_anomaly',\
    #                    ]
    dynamic_features = ["fm_smoothed","vv_smoothed","vh_smoothed",\
                    "blue_smoothed","green_smoothed","red_smoothed","nir_smoothed",\
                    'ndvi_smoothed', 'ndwi_smoothed',\
                    'vv_ndvi_smoothed','vh_ndvi_smoothed',\
                    'vv_red_smoothed','vh_red_smoothed',\
                    'vv_nir_smoothed','vh_nir_smoothed',\
                    'vv_blue_smoothed','vh_blue_smoothed',\
                    'vv_green_smoothed','vh_green_smoothed', 'doy']
    
    static_features = ['slope', 'elevation', 'canopy_height','forest_cover',
                    'silt', 'sand', 'clay', 'latitude', 'longitude']

    os.chdir(dir_data)
    df =make_df(dynamic_features, static_features = static_features,\
                response = response)
    #df['vh_pm_anomaly'] = df['fm_anomaly']+10
    train_x, train_y, test_x, test_y, n_features =\
               build_data(df, columns = dynamic_features+static_features, \
                          response = response, ignore_multi_spec = False)
    #print(len(train_y)+len(test_y))
    
    model = build_model(n_features)
    change_lr = LearningRateScheduler(scheduler)
    filepath = os.path.join(dir_codes, 'model_checkpoint/weights_%s.hdf5'%save_name)
    checkpoint = ModelCheckpoint(filepath, monitor='val_acc', verbose=1, save_best_only=False, mode='max')
    callbacks_list = [checkpoint, change_lr]
    #tbCallBack = k.callbacks.TensorBoard(log_dir='./tb_log', histogram_freq=0, write_graph=True, write_images=False)
    if  load_model&os.path.isfile(filepath):
        model.load_weights(filepath)
        # Compile model (required to make predictions)
        model.compile(loss='mse', optimizer='sgd', metrics=['accuracy'])  
        rmse_diff = pd.read_pickle(os.path.join(dir_codes, \
                    'model_checkpoint/rmse_diff_%s'%save_name))
        print('[INFO] \t Model loaded')
    else:
        if os.path.isfile(filepath):
            if not(overwrite):
                print('[INFO] File path already exists. Try Overwrite = True or change file name')
                raise
        print('[INFO] \t Retraining Model...')
        model.fit(train_x,train_y, validation_data = (test_x, test_y),  epochs=epochs, \
          batch_size=batch_size, callbacks=callbacks_list, verbose = True)
        rmse_diff, model_rmse = infer_importance(model, train_x, train_y, \
             test_x, test_y, change_lr = change_lr, retrain = True,\
             retrain_epochs = retrain_epochs,  batch_size = batch_size)
        rmse_diff.to_pickle(os.path.join(dir_codes, 'model_checkpoint/rmse_diff_%s'%save_name))
    pred_y = model.predict(test_x).flatten()
    model_rmse = np.sqrt(mean_squared_error(test_y, pred_y))
#    rmse_diff, model_rmse = infer_importance_by_var_category(model, train_x, train_y, \
#             test_x, test_y, batch_size = batch_size, retrain_epochs = retrain_epochs, \
#             change_lr = change_lr, retrain = False)
    ######################################################## make_plots=
    if plot:
        sns.set(font_scale=2.1, style = 'ticks')
        plot_pred_actual(test_y, pred_y, r2_score(test_y, pred_y), model_rmse,\
                     axis_lim = [0,300],xlabel = "FMC", zoom = 1.5, \
                     figname=os.path.join(dir_figures, 'pred_actual_raw_FMC.tiff'), dpi = 72)
        #landcover_wise_pred(test_y, pred_y)
        plot_importance(rmse_diff, model_rmse, xlabel = "RMSE (% FMC)",\
                        zoom = 1.5, dpi = 72,\
                     figname=os.path.join(dir_figures, 'importance_raw_FMC.tiff'))
#        #plot_errors_spatially(test_x, test_y, pred_y)
#        sns.set(font_scale=2, style = 'ticks')
#        anomaly = decompose_plot_pred_actual(pred_y, test_y, df, dpi = 72)
