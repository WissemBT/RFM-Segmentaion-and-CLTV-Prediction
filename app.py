from email import header
from flask import Flask, render_template,request,redirect,url_for,current_app,send_from_directory,send_file,make_response
import pandas as pd
from werkzeug.utils import secure_filename
import os
import model


UPLOAD_FOLDER = 'files'
ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def hello():
    # if request.method=="POST":
    #     n=oneMonth[oneMonth['CustomerID']==request.form["customerID"]].clv
    return render_template("index.html")

@app.route("/",methods=['POST'])
def submit():
    if request.method=="POST":
        if request.form["customerID"]!='':
            df=pd.read_csv('{}/final_cltv.csv'.format(app.config['UPLOAD_FOLDER']))
            ids=df.CustomerID.unique()
            id=float(request.form["customerID"].strip())
            bo=False
            oneM=0
            sixM=0
            oneY=0
            seg=''
            if id in ids: 
                oneM=df[df['CustomerID']==id].cltvOneMonth.values[0]
                sixM=df[df['CustomerID']==id].cltvSixMonths.values[0]
                oneY=df[df['CustomerID']==id].cltvOneYear.values[0]
                seg=df[df['CustomerID']==id].Segment.values[0]
                bo=True
            return render_template("index.html",id=id,ids=ids,oneM=oneM,sixM=sixM,oneY=oneY,bo=bo,seg=seg)


    return render_template("index.html")

@app.route("/segmentrfm",methods=['POST'])
def upload():
    if request.method == 'POST':
        file=request.files['dataRFM']
        if file and allowed_file(file.filename):
                filename= secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                df=pd.read_csv('files/{}'.format(filename))
                verif=True
                final_rfm=model.segment_rfm(df)
                top_10_rfm=final_rfm.sort_values('RFM_SCORE',ascending=False).reset_index()[:10]
                top_10_rfm=top_10_rfm.set_index('CustomerID')
                return render_template("index.html",filename=filename,verif=verif,tables=[top_10_rfm.to_html(classes='data')], header="true")
                top_10_rfm=model.best_10_rfm(final_rfm)[:2]
                top_10_rfm=top_10_rfm.set_index('CustomerID')[:2]
                # resp = make_response(final_rfm.to_csv())
                # resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
                # resp.headers["Content-Type"] = "text/csv"
                # return resp
                return render_template("index.html",filename=filename,verif=verif,tables=[top_10_rfm.to_html(classes='data')], header="true")
        elif file and allowed_file(file.filename)==False:
                return render_template("index.html",filebadr=True)
        else:
                return render_template("index.html",notsubmitr=True)
@app.route("/segmentcltv",methods=['POST'])
def cltv():
    if request.method == 'POST':
        if 'dataCLTV'in request.files:
            file=request.files['dataCLTV']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                df=pd.read_csv('files/{}'.format(filename))
                verif=True
                final_cltv=model.segment_cltv(df)
                top_10_cltv=model.best_10_cltv(final_cltv)
                top_10_cltv=top_10_cltv.set_index('CustomerID')
                return render_template("index.html",filename=filename,verify=verif,tables=[top_10_cltv.to_html(classes='data')], header="true")
                # resp = make_response(final_cltv.to_csv())
                # resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
                # resp.headers["Content-Type"] = "text/csv"
                # return resp
            elif file and allowed_file(file.filename)==False:
                return render_template("index.html",filebadc=True)
            else:
                return render_template("index.html",notsubmitc=True)
@app.route('/rfm', methods=['GET', 'POST'])
def download():
    # Appending app path to upload folder path within app root folder
    # uploads = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    # Returning file from appended path
    # return send_from_directory(directory=uploads, filename=file)
    return send_file("{}/{}".format(app.config['UPLOAD_FOLDER'],'final_rfm.csv'))
@app.route('/cltv', methods=['GET', 'POST'])
def downloadcltv():
    # Appending app path to upload folder path within app root folder
    # uploads = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    # Returning file from appended path
    # return send_from_directory(directory=uploads, filename=file)
    return send_file("{}/{}".format(app.config['UPLOAD_FOLDER'],'final_cltv.csv'))   
@app.route('/path')
def path():
    return os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])



if __name__ == "__main__":
    app.run(debug=True)
