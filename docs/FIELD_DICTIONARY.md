# Field Dictionary

This document describes fields exported in comment CSV/XLSX files.

| Field | Description |
| --- | --- |
| `video_id` | Video identifier supplied by the task or local fixture. |
| `comment_id` | Unique identifier for the exported comment within the accessible data source. |
| `root_comment_id` | First-level comment ID for the current comment tree. |
| `parent_comment_id` | Direct parent comment ID. Empty for first-level comments. |
| `reply_to_comment_id` | Comment ID that this row replies to, when available. |
| `reply_to_user_name` | Display name of the user being replied to, when available. |
| `depth` | Comment tree depth: `1` for first-level, `2` for second-level, `3` for third-level, `4` for fourth-level. |
| `comment_path` | Tree position such as `1`, `1.1`, `1.1.1`, or `1.1.1.1`. |
| `comment_user_name` | Comment author's display name as returned by the accessible source. |
| `comment_user_id_hash` | Hashed user identifier. Raw user IDs are not exported. |
| `comment_user_uid_hash` | Hashed UID. Raw UIDs are not exported. |
| `comment_time` | Comment creation time as provided by the input source. |
| `comment_ip_location` | Comment IP location label as provided by the input source. |
| `comment_like_count` | Like count for the comment. |
| `comment_text` | Original comment text, preserved without overwrite. |
| `cleaned_comment_text` | Cleaned comment text after trimming whitespace, normalizing line breaks, and applying configured removals. |
| `text_length` | Character length of `cleaned_comment_text`. |
| `has_emoji` | Whether the original text contains emoji. |
| `has_url` | Whether the original text contains a URL. |
| `has_mention` | Whether the original text contains an `@username` mention. |
| `crawl_time` | UTC timestamp when this row was written by the collector. |
