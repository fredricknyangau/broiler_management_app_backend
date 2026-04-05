from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.community import CommunityPost, CommunityComment, CommunityLike, CommunityCategory
from app.schemas.community import PostCreate, PostResponse, CommentCreate, CommentResponse, CategoryResponse, CommentBase

router = APIRouter()

# --- CATEGORIES ---

@router.get("/categories", response_model=List[CategoryResponse])
async def read_categories(db: AsyncSession = Depends(get_db)):
    """Fetch available discussion categories."""
    result = await db.execute(select(CommunityCategory).order_by(CommunityCategory.name))
    categories = result.scalars().all()
    
    # Simple seeding if empty (for first run)
    if not categories:
        seeds = [
            {"name": "General Discussion", "slug": "general", "description": "Anything about poultry farming", "color": "#4CAF50", "icon": "message-circle"},
            {"name": "Health & Diseases", "slug": "health", "description": "Ask about symptoms and vaccines", "color": "#F44336", "icon": "shield-plus"},
            {"name": "Marketplace", "slug": "market", "description": "Buy/Sell birds and equipment", "color": "#FF9800", "icon": "shopping-bag"},
            {"name": "Success Stories", "slug": "success", "description": "Share your wins with the community", "color": "#9C27B0", "icon": "trophy"},
        ]
        for s in seeds:
            cat = CommunityCategory(**s)
            db.add(cat)
        await db.commit()
        result = await db.execute(select(CommunityCategory).order_by(CommunityCategory.name))
        categories = result.scalars().all()
        
    return categories

# --- POSTS ---

@router.get("/feed", response_model=List[PostResponse])
async def read_feed(
    category_id: Optional[UUID] = None,
    q: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Global community feed with search and categorization."""
    stmt = (
        select(CommunityPost)
        .order_by(CommunityPost.is_pinned.desc(), CommunityPost.created_at.desc())
    )
    
    if category_id:
        stmt = stmt.filter(CommunityPost.category_id == category_id)
    if q:
        stmt = stmt.filter(CommunityPost.title.ilike(f"%{q}%"))
        
    result = await db.execute(stmt.offset(skip).limit(limit))
    posts = result.scalars().all()
    
    # Check likes for current user
    for post in posts:
        like_check = await db.execute(
            select(CommunityLike).filter(
                CommunityLike.post_id == post.id,
                CommunityLike.user_id == current_user.id
            )
        )
        post.liked_by_me = like_check.scalar_one_or_none() is not None
        
    return posts

@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new discussion post."""
    post = CommunityPost(
        **post_in.model_dump(),
        author_id=current_user.id
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post

@router.get("/posts/{post_id}", response_model=PostResponse)
async def read_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed post content and metadata."""
    result = await db.execute(select(CommunityPost).filter(CommunityPost.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    like_check = await db.execute(
        select(CommunityLike).filter(CommunityLike.post_id == post.id, CommunityLike.user_id == current_user.id)
    )
    post.liked_by_me = like_check.scalar_one_or_none() is not None
    return post

# --- INTERACTIONS ---

@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Like or unlike a post."""
    result = await db.execute(select(CommunityPost).filter(CommunityPost.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    like_stmt = select(CommunityLike).filter(
        CommunityLike.post_id == post_id, 
        CommunityLike.user_id == current_user.id
    )
    existing_like = (await db.execute(like_stmt)).scalar_one_or_none()
    
    if existing_like:
        await db.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        action = "unliked"
    else:
        new_like = CommunityLike(post_id=post_id, user_id=current_user.id)
        db.add(new_like)
        post.likes_count += 1
        action = "liked"
        
    await db.commit()
    return {"status": "success", "action": action, "likes_count": post.likes_count}

@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def read_comments(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch comments for a post."""
    result = await db.execute(
        select(CommunityComment)
        .filter(CommunityComment.post_id == post_id)
        .order_by(CommunityComment.created_at.asc())
    )
    return result.scalars().all()

@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def create_comment(
    post_id: UUID,
    comment_in: CommentBase, # Define this in schemas if needed, or use a simple base
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Discuss on a post."""
    post_check = await db.execute(select(CommunityPost).filter(CommunityPost.id == post_id))
    post = post_check.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    comment = CommunityComment(
        post_id=post_id,
        author_id=current_user.id,
        content=comment_in.content
    )
    post.comments_count += 1
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
