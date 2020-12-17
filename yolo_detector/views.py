from django.shortcuts import render, HttpResponse, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers
from django.utils.timezone import now
from django.conf.urls import *

#import necessary modules
import cv2
import numpy as np
from datetime import datetime, timedelta
import os.path
import json

# import the yolo detector file
from module.YoloDetector import YoloDetector
from yolo_detector.forms import loginform #Access login form
from yolo_detector.models import TblAdmin #Access db details through model
from yolo_detector.models import Tblproduct #Access db details through model
from django.contrib import messages

#Base url
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIRS = os.path.join(PROJECT_PATH, 'templates/'),
#print(PROJECT_PATH, TEMPLATE_DIRS, BASE_DIR)

# Create your views here.
def index(request):
    '''index file'''
    if 'session_data' in request.session:
        if request.session['session_data']['admin_logged_in'] == True:
            with open("./static/files/coco.names", 'r') as f:
                classes = [w.strip() for w in f.readlines()]
            return render(request, 'detect.html',{"objects": classes})
    else:        
        return redirect('/login')

def count_cameras():
    '''Get the number of cameras available'''
    max_tested = 100
    for i in range(max_tested):
        temp_camera = cv2.VideoCapture(i)
        if temp_camera.isOpened():
            temp_camera.release()
            continue
        return i

def detect(request):
    '''detect the object'''
    full_filename = ''
    if request.method == 'POST':
        res = request.POST.getlist('classes')
        folder = 'uploads'
        if request.FILES:
            uploaded_filename = request.FILES['video_file'].name

            # create the folder if it doesn't exist.
            try:
                os.mkdir(os.path.join(BASE_DIR, folder))
            except:
                pass

            # save the uploaded file inside that folder.
            full_filename = os.path.join(BASE_DIR, folder, uploaded_filename)
            with open(full_filename, 'wb+') as destination:  
                for chunk in request.FILES['video_file'].chunks():  
                    destination.write(chunk)  

        # read the default classes for the yolo model
        with open("./static/files/coco.names", 'r') as f:
            classes = [w.strip() for w in f.readlines()]
        
        # select specific classes that you want to detect out of the 80 and assign a color to each detection
        selected = {}
        for cls in res:
            selected.update({cls:(0,255,255)})
        
        # initialize the detector with the paths to cfg, weights, and the list of classes
        detector = YoloDetector("./static/files/yolov3-tiny.cfg", "./static/files/yolov3-tiny.weights", classes)
        # initialize video stream
        check_dir = os.path.join(BASE_DIR, folder)

        if os.listdir(check_dir) and full_filename: #Upload video for object detection
            cap  = cv2.VideoCapture(full_filename)
        elif 'webcam' in request.POST: #web cam video for object detection
            if count_cameras() == 1:
                cap = cv2.VideoCapture(0)
            else:#For multiple video capture
                frames = []
                caps = []
                for index in count_cameras():
                    caps.append(cv2.VideoCapture(index))

                for cap in caps:
                    while cap.isOpened():
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frames.append(frame)    
        else:        
            cap = cv2.VideoCapture("./static/videos/input_video.mp4") #static video for object detection
        print(cap.isOpened())
        # read first frame
        ret, frame = cap.read()

        # loop to read frames and update window
        while ret:
            # this returns detections in the format {cls_1:[(top_left_x, top_left_y, top_right_x, top_right_y), ..],
            #                                        cls_4:[], ..}
            # Note: you can change the file as per your requirement if necessary
            detections = detector.detect(frame)
            # loop over the selected items and check if it exists in the detected items, if it exists loop over all the items of the specific class
            # and draw rectangles and put a label in the defined color
            for cls, color in selected.items():
                if cls in detections:
                    for box in detections[cls]:
                        x1, y1, x2, y2 = box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness=1)
                        cv2.putText(frame, cls, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color)
            # display the detections
            cv2.imshow("detections", frame)
            # wait for key press
            key_press = cv2.waitKey(1) & 0xff
            # exit loop if q or on reaching EOF
            if key_press == ord('q'):
                break
            ret, frame = cap.read()
        # release resources
        cap.release()
        # destroy window
        cv2.destroyAllWindows()
        #Remove the files in upload directory 
        for f in os.listdir(check_dir):
            print(f)
            os.remove(os.path.join(check_dir, f))
    return HttpResponse(ret)

def login(request):
    """Admin login functionality"""
    #Check if admin is already login
    if 'session_data' in request.session:
        if request.session['session_data']['admin_logged_in'] == True:
            return HttpResponseRedirect('/')

    #Fetch post value from login form   
    form = loginform(request.POST)
    if request.method == "POST":
        print(request.POST)
        username = request.POST.get("username")
        password = request.POST.get("password")
        #check user name and password is match to db details
        try:
            checklogin = TblAdmin.objects.get(username=username, password=password)
            uname = TblAdmin.objects.all()
            #set session
            session_data = dict(username=uname[0].username, email=uname[0].email, id=uname[0].id, admin_logged_in=True)
            request.session['session_data'] = session_data
            return HttpResponseRedirect('/')    
            #return redirect('/')
        except TblAdmin.DoesNotExist:
            messages.error(request, 'Invalid login. Please try again.')
            return redirect('/login')       
    else:  
        form = TblAdmin()  
    return render(request,'login.html')
    #return render(request, 'login.html')    

def logout(request):
    """Logout the admin and destroy session values"""
    del request.session['session_data']
    return redirect('/login')

def view(request):
    '''table dashboard view'''
    return render(request, 'list.html')   

def list(request):
    '''ajax list of table'''
    #Remove records for last 7 days automatically 
    auto_delete = Tblproduct.objects.filter(created_date__lte=datetime.now()-timedelta(days=7)).delete()
    
    #select and show the records in jquery ajax datatable
    object_list = Tblproduct.objects.all() #or any kind of queryset
    data = serializers.serialize('json', object_list)
    return HttpResponse(data, content_type='application/json')

def auto_delete(request):
    '''click the auto_delete button remove the older records for  1 hour older data from now()'''
    dashboard = Tblproduct.objects.raw('''DELETE FROM tbl_product  WHERE created_date > (now() - interval '7 days')''')
    return redirect('/view')
