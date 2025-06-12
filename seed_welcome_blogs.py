"""
Create welcome blog posts for all tournaments in the database
"""
from models import db, Tournament, BlogPost
from datetime import datetime
import textwrap

def seed_real_blogs():
    """Create a welcome blog post for each tournament"""
    tournaments = Tournament.query.all()
    created_count = 0

    for t in tournaments:
        title = f"Welcome to CourtSide Club at {t.name}"
        slug = f"welcome-{t.slug}"
        
        # Check if blog post already exists
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            continue
            
        content = textwrap.dedent(f"""
            Welcome to CourtSide Club at {t.name}!

            We're thrilled you're thinking about attending {t.name}. CourtSide Club was created to make your tennis experience more social, memorable, and fun — whether you're traveling solo or meeting up with friends.

            By joining, you'll be able to:
            - See who else is attending {t.name}
            - Coordinate sessions and match days
            - Get a free lanyard that makes in-person connections easy
            - Stay in the loop on possible meetups or premium seat opportunities

            Our vision is to create a fan-first experience at the biggest tournaments around the world — and {t.name} is no exception.

            Want to be part of it? Just mark your attendance, order your lanyard, and we'll see you there.

            — The CourtSide Club Team
        """).strip()

        blog = BlogPost(
            title=title,
            slug=slug,
            content=content,
            published=True,
            created_at=datetime.utcnow()
        )
        db.session.add(blog)
        created_count += 1

    db.session.commit()
    return f"Created {created_count} welcome blog posts for tournaments."

if __name__ == "__main__":
    from app import app
    with app.app_context():
        result = seed_real_blogs()
        print(result)