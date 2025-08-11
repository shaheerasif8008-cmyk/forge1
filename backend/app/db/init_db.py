"""Database initialization script for Forge 1."""

import logging

from sqlalchemy.orm import Session

from .models import Tenant, User
from .session import SessionLocal, create_tables

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Initialize the database with tables and initial data."""
    try:
        # Create tables
        create_tables()
        logger.info("Database tables created successfully")

        # Create initial data
        db = SessionLocal()
        try:
            create_initial_data(db)
            logger.info("Initial data created successfully")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def create_initial_data(db: Session) -> None:
    """Create initial data for the application."""
    # Ensure default tenant exists
    default_tenant_id = "default"
    existing_tenant = db.get(Tenant, default_tenant_id)
    if existing_tenant is None:
        tenant = Tenant(id=default_tenant_id, name="Default Tenant")
        db.add(tenant)
        db.commit()
        logger.info("Created default tenant")

    # Check if we already have users
    if db.query(User).first():
        logger.info("Database already has data, skipping user initialization")
        return

    # Create a default admin user
    admin_user = User(
        email="admin@forge1.com",
        username="admin",
        hashed_password="admin",  # In production, this should be properly hashed
        is_active=True,
        is_superuser=True,
        role="admin",
        tenant_id=default_tenant_id,
    )

    db.add(admin_user)
    db.commit()

    logger.info("Created default admin user: admin@forge1.com")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
