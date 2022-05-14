from cv2 import norm
import pandas as pd
import matplotlib.pyplot as plt
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from lifetimes.plotting import plot_period_transactions
import lifetimes
from sklearn.preprocessing import StandardScaler,MinMaxScaler
import sklearn
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cdist
import numpy as np
import datetime as dt
from datetime import date
from sklearn.cluster import KMeans
import dill as pickle




def segment_rfm(data):
	rfm=lifetimes.utils.summary_data_from_transaction_data(data, "CustomerID", "Date", "Total")
	today=date.today()
	final_rfm=data.groupby('CustomerID').agg({'Date': lambda Date: (today - pd.to_datetime(Date).max().date()).days,
                                     'PurchaseID': lambda PurchaseID: PurchaseID.nunique(),
                                     'Total': lambda Total: Total.sum()})
	final_rfm.columns=['Recency','Frequency','Monetary']
	final_rfm["recencyScore"] = pd.qcut(final_rfm['Recency'], 5, labels=[5, 4, 3, 2, 1])
	final_rfm["frequencyScore"] = pd.qcut(final_rfm['Frequency'].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
	final_rfm["monetaryScore"] = pd.qcut(final_rfm['Monetary'], 5, labels=[1, 2, 3, 4, 5])
	final_rfm["RFM_SCORE"]=final_rfm["recencyScore"].astype(int)*0.4+final_rfm["frequencyScore"].astype(int)*0.4+final_rfm["monetaryScore"].astype(int)*0.2
	segments=[]
	for i in list(final_rfm['RFM_SCORE']):
		if i<1.5:
			segments.append('lost_customers')
		elif i<2.5:
			segments.append('good_customers')
		elif i<4.8:
			segments.append('loyal_customers')
		else:
			segments.append('champions')
	final_rfm["SegmentRFM"] = segments
	scaled=pd.DataFrame(MinMaxScaler().fit_transform(final_rfm[['Recency','Frequency','Monetary']]))
	scaled.columns=['scaled_Recency','scaled_Frequency','scaled_Monetary']
	model = pickle.load(open("k_means.pkl", "rb"))
	labels = model.fit_predict(scaled)
	final_rfm['segmentsKM']=labels
	l=list(final_rfm.groupby('segmentsKM').mean().sort_values('Recency').index)
	kmeans_segments = {
    l[3]:'lost_customers',
    l[2]:'good_customers',
    l[1]: 'loyal_customers',
    l[0]: 'champions'
	}
	final_rfm['KMeansSegments'] = final_rfm['segmentsKM'].replace(kmeans_segments, regex=True)
	final_rfm.drop('segmentsKM',axis=1,inplace=True)
	final_rfm.to_csv('./files/final_rfm.csv')
	return final_rfm
def segment_cltv(data):
	cltv_df=lifetimes.utils.summary_data_from_transaction_data(data, "CustomerID", "Date", "Total")
	cltv_df["monetary_value"] = cltv_df["monetary_value"] / cltv_df["frequency"]
	cltv_df=cltv_df.dropna()
	bgf=pickle.load(open("bgf.pkl","rb"))
	#bgf.fit_partial(cltv_df['frequence'],cltv_df['recency'],cltv['T'])
	cltv_df["expectedPurchaseOneWeek"] = bgf.predict(1,cltv_df['frequency'],cltv_df['recency'],cltv_df['T'])
	cltv_df["expectedPurchaseOneMonth"] = bgf.predict(4,cltv_df['frequency'],cltv_df['recency'],cltv_df['T'])
	ggf=pickle.load(open("gamma_model.pkl","rb"))
	#ggf.fit_partial(cltv_df['frequency'],cltv_df['monetary_value'])
	cltv_df["expectedAverageProfit"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],cltv_df['monetary_value'])
	cltvOneMonth = ggf.customer_lifetime_value(bgf,cltv_df['frequency'],cltv_df['T'],cltv_df['recency'],cltv_df['monetary_value'],
                                   time=1,freq="W",discount_rate=0.01)
	cltvOneMonth = cltvOneMonth.reset_index()
	cltvFinalOneMonth = cltv_df.merge(cltvOneMonth, on="CustomerID", how="left")
	scaler = MinMaxScaler(feature_range=(0, 5))
	scaler.fit(cltvFinalOneMonth[["clv"]])
	cltvFinalOneMonth["scaledCLV"] = scaler.transform(cltvFinalOneMonth[["clv"]])
	cltvFinalOneMonth["segmentOneMonth"] = pd.qcut(cltvFinalOneMonth["scaledCLV"], 4, labels=["D", "C","B", "A"])
	cltvOneYear = ggf.customer_lifetime_value(bgf,cltv_df['frequency'],cltv_df['T'],cltv_df['recency'],cltv_df['monetary_value'],
                                   time=12,freq="W",discount_rate=0.01)
	cltvOneYear = cltvOneYear.reset_index()
	cltvFinalOneYear = cltv_df.merge(cltvOneYear, on="CustomerID", how="left")
	scaler = MinMaxScaler(feature_range=(0, 5))
	scaler.fit(cltvFinalOneYear[["clv"]])
	cltvFinalOneYear["scaledCLV"] = scaler.transform(cltvFinalOneYear[["clv"]])
	cltvFinalOneYear["segmentOneYear"] = pd.qcut(cltvFinalOneYear["scaledCLV"], 4, labels=["D", "C","B", "A"])
	cltvSixMonths = ggf.customer_lifetime_value(bgf,cltv_df['frequency'],cltv_df['T'],cltv_df['recency'],cltv_df['monetary_value'],
                                   time=6,freq="W",discount_rate=0.01)
	cltvSixMonths= cltvSixMonths.reset_index()
	cltvFinalSixMonths= cltv_df.merge(cltvSixMonths, on="CustomerID", how="left")
	scaler = MinMaxScaler(feature_range=(0, 5))
	scaler.fit(cltvFinalSixMonths[["clv"]])
	cltvFinalSixMonths["scaledCLV"] = scaler.transform(cltvFinalSixMonths[["clv"]])
	cltvFinalSixMonths["segmentOneYear"] = pd.qcut(cltvFinalSixMonths["scaledCLV"], 4, labels=["D", "C","B", "A"])
	final_cltv=pd.DataFrame({"CustomerID":cltvFinalSixMonths.CustomerID,"cltvOneMonth":cltvFinalOneMonth.clv,"cltvSixMonths":cltvFinalSixMonths.clv,"cltvOneYear":cltvFinalOneYear.clv,"Segment":cltvFinalOneYear.segmentOneYear})
	final_cltv.to_csv('./files/final_cltv.csv',index=False)
	return final_cltv
def best_10_rfm(data):
	output=data.sort_values('RFM_SCORE',ascending=False)[:10]
	return output
def best_10_cltv(data):
	output=data.sort_values('cltvOneYear',ascending=False)[:10]
	return output

# df=pd.read_csv('final_rfm.csv')
# print(best_10_rfm(df))
# df=pd.read_csv('files/final_rfm.csv')

# print(l)
# print(df.groupby('KMeansSegments').count())