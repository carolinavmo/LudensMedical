from app import app  # noqa: F401

# Import routes
import routes  # noqa: F401

# Import course wizard routes
import routes_course_wizard  # noqa: F401

# Import standalone quiz management routes
import routes_standalone_quiz  # noqa: F401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
