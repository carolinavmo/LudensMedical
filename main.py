from app import app  # noqa: F401

# Import routes
import routes  # noqa: F401

# Import course wizard routes
import routes_course_wizard  # noqa: F401

# Standalone quiz management routes have been removed

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
