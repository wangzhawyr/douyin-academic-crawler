"""Data models used by comment collection, parsing, and storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CommentNode:
    """A normalized comment parsed from an accessible platform response."""

    comment_id: str
    user_name: str
    user_id: Optional[str] = None
    user_uid: Optional[str] = None
    sec_uid: Optional[str] = None
    comment_time: Optional[str] = None
    ip_location: Optional[str] = None
    like_count: int = 0
    text: str = ""
    reply_to_comment_id: Optional[str] = None
    reply_to_user_name: Optional[str] = None


RawComment = CommentNode


@dataclass(frozen=True)
class TraversalNode:
    """A comment queued for child-reply traversal."""

    raw: RawComment
    depth: int
    root_comment_id: str
    parent_comment_id: Optional[str]
    comment_path: str


@dataclass(frozen=True)
class CommentRecord:
    """A privacy-preserving CSV/Excel-ready comment row."""

    video_id: str
    comment_id: str
    root_comment_id: str
    parent_comment_id: str
    reply_to_comment_id: str
    reply_to_user_name: str
    depth: int
    comment_path: str
    comment_user_name: str
    comment_user_id_hash: str
    comment_user_uid_hash: str
    comment_time: str
    comment_ip_location: str
    comment_like_count: int
    comment_text: str
    crawl_time: str
