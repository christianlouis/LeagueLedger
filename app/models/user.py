# Add is_admin field to User model if it's missing

from sqlalchemy import Column, Integer, String, Boolean
# ...existing imports...

class User(Base):
    __tablename__ = "users"
    
    # ...existing fields...
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    password = Column(String(255))
    
    # Add is_admin field if it doesn't exist
    is_admin = Column(Boolean, default=False)
    
    # ...existing methods...
