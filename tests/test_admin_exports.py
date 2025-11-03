import pytest
from flask import url_for
from app.models import User, ContinuousTrainingEvent, UserContinuousTraining, ContinuousTrainingType, UserContinuousTrainingStatus
from datetime import datetime, timedelta, timezone
import openpyxl
import io

def test_export_user_summary(client, admin_user, user_factory, db):
    """
    Test the export_user_summary functionality to ensure it includes
    study level and total continuous training hours for the last 6 years.
    """
    # Create a test user with specific data
    test_user = user_factory(
        full_name="Test User",
        email="test@example.com",
        study_level="Master's Degree",
        is_approved=True
    )
    db.session.add(test_user)
    db.session.commit()

    # Add continuous training data for the test user
    # Training 1: 3 years ago, 10 hours, Presential
    event1_date = datetime.now(timezone.utc) - timedelta(days=3*365)
    event1 = ContinuousTrainingEvent(
        title="Event 1",
        description="Desc 1",
        training_type=ContinuousTrainingType.PRESENTIAL,
        event_date=event1_date,
        duration_hours=10.0,
        creator=admin_user,
        status=UserContinuousTrainingStatus.APPROVED
    )
    db.session.add(event1)
    db.session.flush() # To get event1.id

    user_ct1 = UserContinuousTraining(
        user=test_user,
        event=event1,
        status=UserContinuousTrainingStatus.APPROVED,
        validated_hours=10.0,
        validated_by=admin_user,
        validation_date=datetime.now(timezone.utc)
    )
    db.session.add(user_ct1)

    # Training 2: 1 year ago, 5 hours, Online
    event2_date = datetime.now(timezone.utc) - timedelta(days=1*365)
    event2 = ContinuousTrainingEvent(
        title="Event 2",
        description="Desc 2",
        training_type=ContinuousTrainingType.ONLINE,
        event_date=event2_date,
        duration_hours=5.0,
        creator=admin_user,
        status=UserContinuousTrainingStatus.APPROVED
    )
    db.session.add(event2)
    db.session.flush() # To get event2.id

    user_ct2 = UserContinuousTraining(
        user=test_user,
        event=event2,
        status=UserContinuousTrainingStatus.APPROVED,
        validated_hours=5.0,
        validated_by=admin_user,
        validation_date=datetime.now(timezone.utc)
    )
    db.session.add(user_ct2)
    db.session.commit()

    # Log in as admin
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['_fresh'] = True

    # Make the request to the export endpoint
    response = client.get(url_for('admin.export_user_summary'))
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment' in response.headers['Content-Disposition']

    # Parse the Excel file
    workbook = openpyxl.load_workbook(io.BytesIO(response.data))
    sheet = workbook.active

    # Get headers
    headers = [cell.value for cell in sheet[1]]
    assert "Study Level" in headers
    assert "Total Continuous Training Hours (Last 6 Years)" in headers

    # Find the row for the test user
    user_row = None
    for row_idx in range(2, sheet.max_row + 1):
        row_data = [cell.value for cell in sheet[row_idx]]
        if row_data[headers.index("Email")] == test_user.email:
            user_row = row_data
            break
    
    assert user_row is not None, "Test user not found in the exported summary."

    # Assert the values
    assert user_row[headers.index("Study Level")] == test_user.study_level
    # The total hours should be 10.0 (event1) + 5.0 (event2) = 15.0
    assert user_row[headers.index("Total Continuous Training Hours (Last 6 Years)")] == 15.0
