"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse,
                         HttpResponseNotAllowed)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from app.models import InstructorProfile, StudentProfile, Course, Lecture, QRCodeUpload
from datetime import datetime
import zoneinfo
import json
import io
import uuid

# from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
#                      Lecture, QRCodeUpload, is_instructor, is_student,
#                      getUploadsForCourse)

CDT = zoneinfo.ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Render the home page (index.html)."""
    curr_time = datetime.now(CDT).strftime('%H:%M')
    
    context = {
        'curr_time': curr_time,
        'user': request.user,
    }
    
    return render(request, 'app/index.html', context)


def time_view(request):
    return HttpResponse(datetime.now(CDT).strftime('%H:%M'))


def sum_view(request):
    n1 = float(request.GET.get('n1'))
    n2 = float(request.GET.get('n2'))
    total = round(n1 + n2, 3)
    
    return HttpResponse(total)


# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------
def new_user_view(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    
    return render(request, 'app/new.html')


@csrf_exempt
def createUser(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    user_name = request.POST.get('user_name')
    email = request.POST.get('email')
    password = request.POST.get('password')
    is_student = request.POST.get('is_student')
    
    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest("Email is already registered.")
    
    user = User.objects.create_user(username=user_name, email=email, password=password)
    
    if is_student == '1':
        StudentProfile.objects.create(user=user)
    else:
        InstructorProfile.objects.create(user=user)
    
    login(request, user)
    
    return HttpResponse("User created successfully.", status=200)


# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------
def new_course_view(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    
    return render(request, 'app/new_course.html')


@csrf_exempt
def createCourse(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    if not request.user.is_authenticated or not hasattr(request.user, 'instructorprofile'):
        return HttpResponse('Unauthorized', status=401)
    
    course_name = request.POST.get('course-name')
    start_time = request.POST.get('start-time')
    end_time = request.POST.get('end-time')
    days = []
    
    for day in ['day-mon', 'day-tue', 'day-wed', 'day-thu', 'day-fri']:
        if request.POST.get(day):
            days.append(day.replace('day-', '').upper())
    
    schedule_str = f'{start_time}-{end_time} ' + ','.join(days) if start_time and end_time else ''
    instructor_profile = InstructorProfile.objects.get(user=request.user)
    
    Course.objects.create(
        name=course_name,
        instructor=instructor_profile,
        schedule=schedule_str
    )
    
    return HttpResponse('Course created successfully.', status=200)


def new_lecture_view(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    
    return render(request, 'app/new_lecture.html')


@csrf_exempt
def createLecture(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    if not request.user.is_authenticated or not hasattr(request.user, 'instructorprofile'): 
        return HttpResponse("Unauthorized", status=401)
    
    course_name = request.POST.get('choice')
    
    try:
        course = Course.objects.get(name=course_name)
    except Course.DoesNotExist:
        return HttpResponseBadRequest('Course not found.')
    
    qr_id = str(uuid.uuid4())
    lecture_date = datetime.now(CDT).date()
    
    Lecture.objects.create(
        course=course,
        date=lecture_date,
        qr_identifier=qr_id
    )
    
    return HttpResponse('Lecture created successfully.', status=200)


def new_qr_upload_view(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    
    return render(request, 'app/new_qr_upload.html')


@csrf_exempt
def createQRCodeUpload(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    if not request.user.is_authenticated or not hasattr(request.user, 'studentprofile'):
        return HttpResponse('Unauthorized', status=401)
    
    image_file = request.FILES.get('imageUpload')
    if not image_file:
        return HttpResponseBadRequest('Missing imageUpload file.')
    
    student_profile = StudentProfile.objects.get(user=request.user)
    
    QRCodeUpload.objects.create(
        student=student_profile,
        qr_code=image_file
    )
    
    return HttpResponse('QR Code uploaded successfully.', status=200)


def dumpUploads(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    
    if not request.user.is_authenticated or not hasattr(request.user, 'instructorprofile'):
        return HttpResponse('Unauthorized', status=401)
    
    uploads = QRCodeUpload.objects.select_related('student__user').all()
    data = []
    
    for upload in uploads:
        data.append({
            'username': upload.student.user.username,
            'upload_time': upload.uploaded_at.isoformat()
        })
        
    return JsonResponse(data, safe=False)


# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



