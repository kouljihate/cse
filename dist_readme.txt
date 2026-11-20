Document Manager — Standalone Package
=====================================

This folder contains the Document Manager backend compiled into a
standalone executable. No Python or dependencies are required.


PREREQUISITES (on the target machine)
--------------------------------------
- Windows 10/11 64-bit
- MongoDB running on a known IP address (e.g. 192.168.1.100:27017)


SETUP
------
1. Copy the entire "docmanager" folder to the target machine.

2. Rename ".env.example" to ".env" and edit the MongoDB host:

       MONGO_HOST=192.168.1.100
       JWT_SECRET_KEY=change-this-to-a-random-secret
       JWT_ACCESS_TOKEN_EXPIRES=86400

3. (Optional) Create a "requests" folder next to docmanager.exe if
   you plan to use the Request Management feature. This folder
   should be a Git repository for auto-push to work.


RUN
----
Open a terminal in the docmanager folder and run:

    docmanager.exe --db-host 192.168.1.100

Optional flags:

    --host 0.0.0.0    Interface to bind (default: 127.0.0.1)
    --port 5000       Change port (default: 5000)
    --debug           Enable debug output

Then open http://localhost:5000 in a browser.


FIRST USE
----------
1. Run the backend once (it will create collections automatically).
2. Register the first admin account at /register.
3. Use the seed script if you need a default admin:

   Python: backend/seed.py  (requires Python)
   Or register manually via the web UI.


DOCKER (recommended for local use)
----------------------------------
From the repository root:

    docker compose up --build

Then open http://localhost:5000. MongoDB data and uploaded documents
are kept in Docker volumes / mounted folders.


NOTES
------
- The executable connects to MongoDB at the specified host.
  MongoDB must already be installed and running on that host.
- All data resides in MongoDB, not in the app folder.
- To update, just replace the executable and data files.
