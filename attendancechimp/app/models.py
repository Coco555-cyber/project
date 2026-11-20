"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import string
import random
from datetime import datetime, time
import zoneinfo

logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------
class InstructorProfile(models.Model):
    """
    Model for instructor profiles
    
    Fields:
        user: User account of the instructor
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class StudentProfile(models.Model):
    """
    Model for Student profiles
    
    Fields:
        user: User account of the student
        grade: Grade of the student
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    grade = models.CharField(max_length=10)



# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------
class Course(models.Model):
    """
    Model for instructor profiles
    
    Fields:
        name: Name of the course
        instructor: Instructor of the course
        schedule: Schedule of course
    """
    name = models.CharField(max_length=50)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.CASCADE)
    schedule = models.CharField(max_length=100)
    course = models.CharField(max_length=50)
    startTime = models.TimeField()
    endTime = models.TimeField()
    mon = models.BooleanField(default=False)
    tue = models.BooleanField(default=False)
    wed = models.BooleanField(default=False)
    thu = models.BooleanField(default=False)
    fri = models.BooleanField(default=False)



# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------
class Enrollment(models.Model):
    """
    Model for student enrollments
    
    Fields:
        student: Student enrolled in the course
        course: Course the student is enrolled in
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)



# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
class Lecture(models.Model):
    """
    Model for course lectures
    
    Fields:
        course: Course of the lecture
        date: Date of the lecture
        qr_identifier: QR code for the lecture
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    qr_identifier = models.CharField(max_length=255)



# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------
class QRCodeUpload(models.Model):
    """
    Model for QR code uploads submitted by students
    
    Fields:
        student: Student that uploaded the QR code
        lecture: Lecture associated with the uploaded QR code
        qr_code: QR code
        uploaded_at: Time of upload
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, null=True, blank=True)
    qr_code = models.ImageField()
    uploaded_at = models.DateTimeField(auto_now_add=True)



# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------
def get_user_role(user):
    """
    Returns the role of the user
    """
    if hasattr(user, 'instructorprofile'):
        return 'instructor'
    
    if hasattr(user, 'studentprofile'):
        return 'student'
    
    return None



def getUploadsForCourse(course):
    """
    Return a list of valid QRCodeUpload objects for the given course number.
    """
    course_obj = Course.objects.filter(course=course).first()
    if not course_obj:
        return []
    
    start_val = getattr(course_obj, "startTime", None)
    end_val = getattr(course_obj, "endTime", None)
    
    if start_val:
        start_val = datetime.strptime(start_val.strip(), "%H:%M").time()
    if end_val:
        end_val = datetime.strptime(end_val.strip(), "%H:%M").time()
    if not isinstance(start_val, time) or not isinstance(end_val, time):
        return []
    
    day_attr_by_weekday = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
    }
    
    uploads = (
        QRCodeUpload.objects.filter(lecture__course=course_obj)
        .select_related("lecture", "lecture__course", "student")
        .order_by("uploaded_at")
    )
    
    local_time = zoneinfo.ZoneInfo("America/Chicago")
    valid_uploads = []
    
    for upload in uploads:
        if upload.uploaded_at is None:
            continue
        
        ts = upload.uploaded_at
        if timezone.is_aware(ts):
            ts = ts.astimezone(local_time)
        else:
            ts = ts.replace(tzinfo=local_time)
        
        day_attr = day_attr_by_weekday.get(ts.weekday())
        if not day_attr or not getattr(course_obj, day_attr, False):
            continue
        
        upload_time = ts.time()
        if start_val <= upload_time <= end_val:
            valid_uploads.append(upload)
    
    return valid_uploads