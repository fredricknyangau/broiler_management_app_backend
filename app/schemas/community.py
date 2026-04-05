from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional

# --- CATEGORY ---
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    color: str = "#4CAF50"
    icon: Optional[str] = "layers"

class CategoryResponse(CategoryBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# --- USER MINI PROFILE ---
class AuthorMini(BaseModel):
    id: UUID
    full_name: Optional[str] = None
    role: str = "FARMER"
    model_config = ConfigDict(from_attributes=True)

# --- COMMENT ---
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    post_id: UUID

class CommentResponse(CommentBase):
    id: UUID
    post_id: UUID
    author_id: UUID
    author: AuthorMini
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- POST ---
class PostBase(BaseModel):
    title: str
    content: str
    category_id: Optional[UUID] = None
    image_url: Optional[str] = None
    images: List[str] = []

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_closed: Optional[bool] = None

class PostResponse(PostBase):
    id: UUID
    author_id: UUID
    author: AuthorMini
    category: Optional[CategoryResponse] = None
    likes_count: int = 0
    comments_count: int = 0
    is_pinned: bool = False
    is_closed: bool = False
    created_at: datetime
    
    # Check if liked by current user (injected in router)
    liked_by_me: bool = False
    
    model_config = ConfigDict(from_attributes=True)
