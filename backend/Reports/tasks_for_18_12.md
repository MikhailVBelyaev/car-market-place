# Task Plan for Tomorrow

## 1. Add Link to Model `Car` and PostgreSQL, Create Update for DB Directory
- **Objective**: Ensure that the `Car` model is correctly linked to PostgreSQL.
- **Steps**:
  1. Update the `Car` model and run `python manage.py makemigrations`.
  2. Apply migrations using `python manage.py migrate`.
  3. Verify that new data is being saved in the PostgreSQL `cars` table by checking the data via Django admin or PostgreSQL (`SELECT * FROM cars;`).

## 2. Remove or Modify Sensitive Information About User DB and Password
- **Objective**: Ensure that sensitive data like database credentials are not exposed on GitHub.
- **Steps**:
  1. Use `.env` files or Django settings to securely manage credentials.
  2. Remove any hardcoded sensitive information from the repository (e.g., `.gitignore` the `.env` file).
  3. Double-check repository settings and remove any exposed credentials.

## 3. Create Periodic Task for Saving Data (Every 10 Minutes)
- **Objective**: Set up periodic tasks to save data regularly.
- **Steps**:
  1. Install and configure `Celery` with `django-celery-beat`.
  2. Create a periodic task for saving data to the database every 10 minutes.
  3. Test the periodic task to ensure it’s running as expected.

## 4. UI (Frontend) in a Separate Directory
- **Objective**: Set up frontend and connect it to the Django project.
- **Steps**:
  1. Create a separate directory for the frontend (e.g., React, Vue, or simple HTML).
  2. Connect frontend to Django backend via API or server-rendered pages.
  3. Test communication between frontend and backend.

## 5. Check Data Visibility on Ubuntu Server via Local Network
- **Objective**: Ensure that the Django app is accessible from other machines in the local network.
- **Steps**:
  1. Configure `ALLOWED_HOSTS` in `settings.py` to allow access from the local network.
  2. Run the Django server using `python manage.py runserver 0.0.0.0:8000`.
  3. Check if the app is accessible from other devices in the same network using the host machine’s IP address.

---

### Additional Notes:
- **Security Check**: Review database credentials for security.
- **Testing**: Perform end-to-end testing of periodic tasks, frontend-backend connection, and network access.