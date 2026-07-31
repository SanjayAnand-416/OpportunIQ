"""Seed a realistic CSE-student demo dataset into the OpportunIQ SQLite database.

Populates, against the schema owned by ``app.database``:
    - 2  student_profiles  (final/pre-final year CSE students)
    - 15 opportunities     (internships, full-time roles, hackathons)
    - 10 emails            (Gmail notices referencing those opportunities)
    - 5  deadlines         (extracted from a subset of those emails)
    - 8  reminders         (a.k.a. "notifications" in the product spec —
                             this schema's closest table: channel + status +
                             scheduled/sent timestamps against a deadline)

Idempotent: re-running clears and re-inserts the same demo rows instead of
accumulating duplicates, keyed by natural identifiers (profile_id,
(source, external_id), gmail_message_id) or, for deadlines/reminders (which
have no natural key in this schema), by deleting prior demo rows before
re-inserting.

Usage:
    python -m app.scripts.seed_demo_data
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.database import get_db, init_db

logger = logging.getLogger(__name__)

# Tag used to find-and-replace demo deadlines/reminders on re-run; that
# table has no natural unique key to upsert against.
_DEMO_DEADLINE_SOURCE = "demo-seed"


def _skills(*items: str) -> str:
    """Serialize a skills/target_roles list the way profile_repository does."""
    return json.dumps(list(items))


STUDENT_PROFILES = [
    {
        "profile_id": "demo-student-ananya",
        "name": "Ananya Sharma",
        "email": "ananya.sharma.cse@gmail.com",
        "year_of_study": "4th Year",
        "graduation_year": 2026,
        "degree": "B.Tech Computer Science and Engineering",
        "college": "Amrita Vishwa Vidyapeetham, Coimbatore",
        "target_roles": _skills(
            "Software Engineer", "Machine Learning Engineer", "Backend Developer"
        ),
        "skills": _skills(
            "Python",
            "Java",
            "JavaScript",
            "React",
            "Node.js",
            "SQL",
            "Git",
            "Machine Learning",
            "Data Structures & Algorithms",
            "REST APIs",
        ),
        "location": "Coimbatore, Tamil Nadu",
        "opportunity_type": "Internship",
    },
    {
        "profile_id": "demo-student-rohan",
        "name": "Rohan Verma",
        "email": "rohan.verma.dev@gmail.com",
        "year_of_study": "3rd Year",
        "graduation_year": 2027,
        "degree": "B.Tech Computer Science and Engineering",
        "college": "VIT Vellore",
        "target_roles": _skills("Backend Developer", "SDE", "Cloud Engineer"),
        "skills": _skills(
            "C++",
            "Python",
            "Data Structures & Algorithms",
            "Competitive Programming",
            "Docker",
            "AWS",
            "MySQL",
            "Linux",
            "System Design",
        ),
        "location": "Vellore, Tamil Nadu",
        "opportunity_type": "Internship",
    },
]

# (source, external_id) is the natural key opportunities upserts against.
OPPORTUNITIES = [
    dict(
        source="company-portal",
        external_id="amazon-sde-intern-2026",
        title="SDE Intern",
        organization="Amazon",
        location="Bengaluru, India",
        url="https://www.amazon.jobs/en/jobs/sde-intern-2026",
        description="6-month SDE internship building customer-facing services at scale. "
        "Strong DSA and one of Java/C++/Python expected.",
        deadline="2026-08-20",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="microsoft-swe-intern-2026",
        title="Software Engineering Intern",
        organization="Microsoft",
        location="Hyderabad, India",
        url="https://careers.microsoft.com/students/us/en/job/swe-intern-2026",
        description="Work with a product engineering team on Azure services. C#/.NET or "
        "equivalent backend experience preferred.",
        deadline="2026-08-25",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="google-ml-intern-2026",
        title="Machine Learning Intern",
        organization="Google",
        location="Bengaluru, India",
        url="https://careers.google.com/jobs/results/ml-intern-2026",
        description="Apply ML to search ranking problems. Familiarity with Python, "
        "TensorFlow/PyTorch, and linear algebra required.",
        deadline="2026-09-01",
        opportunity_type="Internship",
    ),
    dict(
        source="linkedin",
        external_id="flipkart-swe-intern-2026",
        title="SWE Intern",
        organization="Flipkart",
        location="Bengaluru, India",
        url="https://www.flipkartcareers.com/#!/joblist/swe-intern-2026",
        description="Build features for Flipkart's checkout platform. DSA round followed by "
        "two technical interviews.",
        deadline="2026-08-18",
        opportunity_type="Internship",
    ),
    dict(
        source="internshala",
        external_id="razorpay-backend-intern-2026",
        title="Backend Developer Intern",
        organization="Razorpay",
        location="Remote",
        url="https://razorpay.com/jobs/backend-developer-intern-2026",
        description="Work on payment gateway APIs. Node.js or Python, SQL, and REST API "
        "design experience expected.",
        deadline="2026-08-22",
        opportunity_type="Internship",
    ),
    dict(
        source="internshala",
        external_id="swiggy-ds-intern-2026",
        title="Data Science Intern",
        organization="Swiggy",
        location="Bengaluru, India",
        url="https://careers.swiggy.com/jobs/data-science-intern-2026",
        description="Build demand-forecasting models for delivery logistics. Python, "
        "pandas, and SQL required.",
        deadline="2026-09-05",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="zoho-fullstack-intern-2026",
        title="Full Stack Developer Intern",
        organization="Zoho",
        location="Chennai, India",
        url="https://www.zoho.com/careers/fullstack-intern-2026.html",
        description="Own a feature end-to-end across a Java backend and a React frontend.",
        deadline="2026-08-30",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="freshworks-devops-intern-2026",
        title="DevOps Intern",
        organization="Freshworks",
        location="Chennai, India",
        url="https://www.freshworks.com/company/careers/devops-intern-2026",
        description="CI/CD pipelines, Docker, and Kubernetes on AWS infrastructure.",
        deadline="2026-09-10",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="salesforce-cloud-intern-2026",
        title="Cloud Engineering Intern",
        organization="Salesforce",
        location="Hyderabad, India",
        url="https://careers.salesforce.com/en/jobs/cloud-engineering-intern-2026",
        description="Support multi-tenant cloud infrastructure reliability projects.",
        deadline="2026-09-15",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="adobe-sde-new-grad-2026",
        title="Software Developer, New Grad",
        organization="Adobe",
        location="Noida, India",
        url="https://careers.adobe.com/us/en/job/sde-new-grad-2026",
        description="Full-time SDE role on Creative Cloud services for 2026 graduates.",
        deadline="2026-09-20",
        opportunity_type="Full-time",
    ),
    dict(
        source="unstop",
        external_id="sih-2026",
        title="Smart India Hackathon 2026",
        organization="Government of India (AICTE)",
        location="Pan-India (multiple nodal centres)",
        url="https://sih.gov.in/2026",
        description="National-level hackathon; teams of 6 build solutions to government-"
        "posted problem statements across software and hardware tracks.",
        deadline="2026-08-15",
        opportunity_type="Hackathon",
    ),
    dict(
        source="github",
        external_id="gsoc-2026",
        title="Google Summer of Code 2026",
        organization="Google Open Source",
        location="Remote",
        url="https://summerofcode.withgoogle.com/programs/2026",
        description="Contribute to an open-source org's codebase over a 12-week program with "
        "a paid stipend. Requires a submitted project proposal.",
        deadline="2026-08-05",
        opportunity_type="Internship",
    ),
    dict(
        source="unstop",
        external_id="hacknitr-2026",
        title="HackNITR 2026",
        organization="NIT Rourkela",
        location="Remote (online rounds)",
        url="https://hacknitr.com/2026",
        description="36-hour beginner-friendly hackathon with tracks in web, ML, and "
        "blockchain. Team size up to 4.",
        deadline="2026-08-10",
        opportunity_type="Hackathon",
    ),
    dict(
        source="company-portal",
        external_id="iisc-research-intern-2026",
        title="Research Internship",
        organization="Indian Institute of Science (IISc)",
        location="Bengaluru, India",
        url="https://iisc.ac.in/research-internships/2026",
        description="Assist a CSA department lab with a systems/ML research project; "
        "co-authorship possible on resulting publications.",
        deadline="2026-09-25",
        opportunity_type="Internship",
    ),
    dict(
        source="company-portal",
        external_id="goldman-sachs-swe-new-grad-2026",
        title="Software Engineer, New Analyst",
        organization="Goldman Sachs",
        location="Bengaluru, India",
        url="https://www.goldmansachs.com/careers/students/programs/india/new-analyst-2026",
        description="Full-time engineering role on trading platform infrastructure for "
        "2026 graduates. Strong CS fundamentals and one OOP language.",
        deadline="2026-09-30",
        opportunity_type="Full-time",
    ),
]

# gmail_message_id is the natural key emails upsert against.
EMAILS = [
    dict(
        gmail_message_id="18f2a001b1c2d3e4",
        thread_id="thread-amazon-sde-2026",
        sender="no-reply@amazon.jobs",
        subject="Your Application to SDE Intern, Amazon India",
        snippet="Thanks for applying. Complete your online assessment before the link expires...",
        body=(
            "Hi Ananya,\n\nThank you for applying to the SDE Intern role at Amazon India. "
            "Please complete your online coding assessment via the link below before "
            "2026-08-20 23:59 IST. The assessment covers data structures, algorithms, and "
            "system design fundamentals.\n\nBest,\nAmazon University Recruiting"
        ),
        received_at="2026-08-01T10:15:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a002c3d4e5f6",
        thread_id="thread-microsoft-swe-2026",
        sender="talent@microsoft.com",
        subject="Next Steps: Software Engineering Internship Application",
        snippet="Your resume has been shortlisted for the next round...",
        body=(
            "Hello,\n\nCongratulations — your application for the Software Engineering "
            "Intern role has been shortlisted. Please confirm your availability for a "
            "technical interview before 2026-08-25.\n\nRegards,\nMicrosoft Campus Recruiting"
        ),
        received_at="2026-08-02T14:30:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a003d4e5f6a7",
        thread_id="thread-google-ml-2026",
        sender="careers-noreply@google.com",
        subject="Google ML Internship — Application Window Closing Soon",
        snippet="Applications for the Machine Learning Intern role close on Sept 1...",
        body=(
            "Hi,\n\nThis is a reminder that the application window for the Machine Learning "
            "Intern position closes on 2026-09-01. Submit your application and portfolio "
            "before the deadline.\n\nGoogle Careers Team"
        ),
        received_at="2026-08-10T09:00:00+05:30",
        is_processed=0,
    ),
    dict(
        gmail_message_id="18f2a004e5f6a7b8",
        thread_id="thread-flipkart-swe-2026",
        sender="hr@flipkartcareers.com",
        subject="Flipkart SWE Intern — Online Assessment Invite",
        snippet="You're invited to take the HackerEarth coding assessment...",
        body=(
            "Hi Ananya,\n\nAs part of your SWE Intern application, please complete the "
            "HackerEarth coding assessment before 2026-08-18 23:59 IST. The test has 3 "
            "coding questions and a 90-minute time limit.\n\nFlipkart Talent Acquisition"
        ),
        received_at="2026-08-03T11:45:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a005f6a7b8c9",
        thread_id="thread-sih-2026",
        sender="noreply@unstop.com",
        subject="Reminder: Smart India Hackathon 2026 Registration Closes in 3 Days",
        snippet="Team registration for SIH 2026 closes on August 15...",
        body=(
            "Hi Rohan,\n\nThis is a reminder that team registration for Smart India "
            "Hackathon 2026 closes on 2026-08-15 23:59 IST. Ensure all 6 team members "
            "and your problem statement selection are finalized before then.\n\nTeam Unstop"
        ),
        received_at="2026-08-12T08:00:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a006a7b8c9d0",
        thread_id="thread-gsoc-2026",
        sender="gsoc-noreply@google.com",
        subject="Google Summer of Code 2026 — Contributor Application Period Open",
        snippet="The contributor application period is open until August 5...",
        body=(
            "Hello,\n\nThe Google Summer of Code 2026 contributor application period is "
            "open. Submit your project proposal to your chosen open-source organization "
            "before 2026-08-05 18:30 UTC.\n\nGSoC Program Administrators"
        ),
        received_at="2026-07-20T06:00:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a007b8c9d0e1",
        thread_id="thread-razorpay-backend-2026",
        sender="notifications@razorpay.com",
        subject="Razorpay Backend Intern — Interview Scheduled",
        snippet="Your technical interview has been scheduled for August 20...",
        body=(
            "Hi Rohan,\n\nYour technical interview for the Backend Developer Intern role "
            "has been scheduled for 2026-08-20 at 3:00 PM IST over Google Meet.\n\n"
            "Razorpay Talent Team"
        ),
        received_at="2026-08-06T16:20:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a008c9d0e1f2",
        thread_id="thread-swiggy-ds-2026",
        sender="careers@swiggy.in",
        subject="Swiggy Data Science Internship — Application Received",
        snippet="We've received your application for the Data Science Intern role...",
        body=(
            "Hi Ananya,\n\nWe've received your application for the Data Science Intern "
            "role. Our team is reviewing applications and will reach out by 2026-09-05 "
            "with next steps.\n\nSwiggy Careers"
        ),
        received_at="2026-08-14T12:10:00+05:30",
        is_processed=0,
    ),
    dict(
        gmail_message_id="18f2a009d0e1f2a3",
        thread_id="thread-adobe-newgrad-2026",
        sender="talent-acquisition@adobe.com",
        subject="Adobe Software Developer Campus Hiring — Round 1 Results",
        snippet="Congratulations on clearing the online assessment round...",
        body=(
            "Hello,\n\nCongratulations — you have cleared Round 1 (Online Assessment) for "
            "the Software Developer, New Grad role. Round 2 (Technical Interview) details "
            "will follow by 2026-09-20.\n\nAdobe University Recruiting"
        ),
        received_at="2026-08-25T10:00:00+05:30",
        is_processed=1,
    ),
    dict(
        gmail_message_id="18f2a00ae1f2a3b4",
        thread_id="thread-hacknitr-2026",
        sender="hackathons@hacknitr.com",
        subject="HackNITR 2026 — Team Registration Deadline Extended",
        snippet="Good news — team registration has been extended to August 10...",
        body=(
            "Hi Rohan,\n\nDue to popular demand, team registration for HackNITR 2026 has "
            "been extended to 2026-08-10 23:59 IST. Finalize your team and track "
            "selection before then.\n\nHackNITR Organizing Committee"
        ),
        received_at="2026-08-04T18:00:00+05:30",
        is_processed=1,
    ),
]

# Matched 1:1 with a subset of EMAILS above by list position; re-seeded by
# deleting prior _DEMO_DEADLINE_SOURCE rows rather than upserting, since this
# table has no natural unique key.
DEADLINES = [
    dict(
        title="Amazon SDE Intern — Online Assessment",
        deadline_at="2026-08-20T23:59:00+05:30",
        context="Complete the online coding assessment before the link expires.",
        email_gmail_message_id="18f2a001b1c2d3e4",
    ),
    dict(
        title="Flipkart SWE Intern — Assessment Deadline",
        deadline_at="2026-08-18T23:59:00+05:30",
        context="Finish the HackerEarth assessment: 3 questions, 90-minute limit.",
        email_gmail_message_id="18f2a004e5f6a7b8",
    ),
    dict(
        title="Smart India Hackathon 2026 — Team Registration",
        deadline_at="2026-08-15T23:59:00+05:30",
        context="Finalize team of 6 and problem statement selection.",
        email_gmail_message_id="18f2a005f6a7b8c9",
    ),
    dict(
        title="Google Summer of Code 2026 — Proposal Submission",
        deadline_at="2026-08-05T18:30:00+00:00",
        context="Submit project proposal to the chosen open-source organization.",
        email_gmail_message_id="18f2a006a7b8c9d0",
    ),
    dict(
        title="HackNITR 2026 — Team Registration (Extended)",
        deadline_at="2026-08-10T23:59:00+05:30",
        context="Extended deadline; finalize team and track selection.",
        email_gmail_message_id="18f2a00ae1f2a3b4",
    ),
]

# Reminders ("notifications"): channel + timing pairs against a subset of
# the deadlines above, referenced by the deadline's title.
REMINDERS = [
    dict(
        deadline_title="Smart India Hackathon 2026 — Team Registration",
        channel="email",
        message="Reminder: Smart India Hackathon 2026 team registration closes in 3 days "
        "(Aug 15). Finalize your team and problem statement now.",
        scheduled_for="2026-08-12T09:00:00+05:30",
        sent_at="2026-08-12T09:00:03+05:30",
        status="sent",
    ),
    dict(
        deadline_title="Smart India Hackathon 2026 — Team Registration",
        channel="websocket",
        message="1 day left to register your team for Smart India Hackathon 2026!",
        scheduled_for="2026-08-14T09:00:00+05:30",
        sent_at=None,
        status="pending",
    ),
    dict(
        deadline_title="Google Summer of Code 2026 — Proposal Submission",
        channel="email",
        message="Reminder: your GSoC 2026 project proposal is due in 7 days (Aug 5, "
        "18:30 UTC). Draft and get mentor feedback before submitting.",
        scheduled_for="2026-07-29T06:00:00+00:00",
        sent_at="2026-07-29T06:00:05+00:00",
        status="sent",
    ),
    dict(
        deadline_title="Google Summer of Code 2026 — Proposal Submission",
        channel="websocket",
        message="1 day left to submit your GSoC 2026 proposal!",
        scheduled_for="2026-08-04T06:00:00+00:00",
        sent_at=None,
        status="pending",
    ),
    dict(
        deadline_title="Amazon SDE Intern — Online Assessment",
        channel="email",
        message="Your Amazon SDE Intern online assessment closes in 2 days (Aug 20). "
        "Set aside 90 uninterrupted minutes to complete it.",
        scheduled_for="2026-08-18T09:00:00+05:30",
        sent_at="2026-08-18T09:00:04+05:30",
        status="sent",
    ),
    dict(
        deadline_title="Flipkart SWE Intern — Assessment Deadline",
        channel="websocket",
        message="Flipkart SWE Intern assessment closes tomorrow — don't forget to submit!",
        scheduled_for="2026-08-17T09:00:00+05:30",
        sent_at="2026-08-17T09:00:02+05:30",
        status="sent",
    ),
    dict(
        deadline_title="HackNITR 2026 — Team Registration (Extended)",
        channel="email",
        message="HackNITR 2026 team registration has been extended to Aug 10 — you still "
        "have time to lock in your team.",
        scheduled_for="2026-08-08T09:00:00+05:30",
        sent_at="2026-08-08T09:00:01+05:30",
        status="sent",
    ),
    dict(
        deadline_title="HackNITR 2026 — Team Registration (Extended)",
        channel="websocket",
        message="Final call: HackNITR 2026 team registration closes today at 11:59 PM.",
        scheduled_for="2026-08-10T09:00:00+05:30",
        sent_at=None,
        status="pending",
    ),
]


async def seed_student_profiles(db) -> None:
    """Upsert the demo student profiles, keyed by ``profile_id``."""
    for profile in STUDENT_PROFILES:
        await db.execute(
            """
            INSERT INTO student_profiles (
                profile_id, name, email, year_of_study, graduation_year,
                degree, college, target_roles, skills, location, opportunity_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                name = excluded.name,
                email = excluded.email,
                year_of_study = excluded.year_of_study,
                graduation_year = excluded.graduation_year,
                degree = excluded.degree,
                college = excluded.college,
                target_roles = excluded.target_roles,
                skills = excluded.skills,
                location = excluded.location,
                opportunity_type = excluded.opportunity_type,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                profile["profile_id"],
                profile["name"],
                profile["email"],
                profile["year_of_study"],
                profile["graduation_year"],
                profile["degree"],
                profile["college"],
                profile["target_roles"],
                profile["skills"],
                profile["location"],
                profile["opportunity_type"],
            ),
        )
    logger.info("Seeded %d student profile(s)", len(STUDENT_PROFILES))


async def seed_opportunities(db) -> None:
    """Upsert the demo opportunities, keyed by ``(source, external_id)``."""
    for opp in OPPORTUNITIES:
        await db.execute(
            """
            INSERT INTO opportunities (
                source, external_id, title, organization, location, url,
                description, deadline, opportunity_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id) DO UPDATE SET
                title = excluded.title,
                organization = excluded.organization,
                location = excluded.location,
                url = excluded.url,
                description = excluded.description,
                deadline = excluded.deadline,
                opportunity_type = excluded.opportunity_type
            """,
            (
                opp["source"],
                opp["external_id"],
                opp["title"],
                opp["organization"],
                opp["location"],
                opp["url"],
                opp["description"],
                opp["deadline"],
                opp["opportunity_type"],
            ),
        )
    logger.info("Seeded %d opportunity/ies", len(OPPORTUNITIES))


async def seed_emails(db) -> None:
    """Upsert the demo Gmail messages, keyed by ``gmail_message_id``."""
    for email in EMAILS:
        await db.execute(
            """
            INSERT INTO emails (
                gmail_message_id, thread_id, sender, subject, snippet, body,
                received_at, is_processed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gmail_message_id) DO UPDATE SET
                thread_id = excluded.thread_id,
                sender = excluded.sender,
                subject = excluded.subject,
                snippet = excluded.snippet,
                body = excluded.body,
                received_at = excluded.received_at,
                is_processed = excluded.is_processed
            """,
            (
                email["gmail_message_id"],
                email["thread_id"],
                email["sender"],
                email["subject"],
                email["snippet"],
                email["body"],
                email["received_at"],
                email["is_processed"],
            ),
        )
    logger.info("Seeded %d email(s)", len(EMAILS))


async def seed_deadlines_and_reminders(db) -> list[int]:
    """Replace prior demo deadlines/reminders and insert fresh ones.

    Deadlines have no natural unique key in this schema, so demo rows are
    tagged via ``context`` prefix and deleted (reminders first, to respect
    the foreign key) before re-inserting — keeping repeat runs idempotent.

    Returns:
        The ids of the inserted deadline rows, for logging/debugging.
    """
    tagged_title_placeholders = ",".join("?" for _ in DEADLINES)
    demo_titles = [d["title"] for d in DEADLINES]

    await db.execute(
        f"""
        DELETE FROM reminders WHERE deadline_id IN (
            SELECT id FROM deadlines WHERE title IN ({tagged_title_placeholders})
        )
        """,
        demo_titles,
    )
    await db.execute(
        f"DELETE FROM deadlines WHERE title IN ({tagged_title_placeholders})", demo_titles
    )

    email_id_by_gmail_id: dict[str, int] = {}
    cursor = await db.execute("SELECT id, gmail_message_id FROM emails")
    for row in await cursor.fetchall():
        email_id_by_gmail_id[row["gmail_message_id"]] = row["id"]

    deadline_id_by_title: dict[str, int] = {}
    for deadline in DEADLINES:
        email_id = email_id_by_gmail_id.get(deadline["email_gmail_message_id"])
        cursor = await db.execute(
            """
            INSERT INTO deadlines (source, title, deadline_at, context, email_message_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _DEMO_DEADLINE_SOURCE,
                deadline["title"],
                deadline["deadline_at"],
                deadline["context"],
                str(email_id) if email_id else None,
            ),
        )
        deadline_id_by_title[deadline["title"]] = cursor.lastrowid

    for reminder in REMINDERS:
        deadline_id = deadline_id_by_title[reminder["deadline_title"]]
        await db.execute(
            """
            INSERT INTO reminders (deadline_id, channel, message, scheduled_for, sent_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                deadline_id,
                reminder["channel"],
                reminder["message"],
                reminder["scheduled_for"],
                reminder["sent_at"],
                reminder["status"],
            ),
        )

    logger.info(
        "Seeded %d deadline(s) and %d reminder(s)/notification(s)", len(DEADLINES), len(REMINDERS)
    )
    return list(deadline_id_by_title.values())


async def seed_demo_data() -> None:
    """Initialize the schema (if needed) and seed the full demo dataset."""
    await init_db()
    async with get_db() as db:
        await seed_student_profiles(db)
        await seed_opportunities(db)
        await seed_emails(db)
        await seed_deadlines_and_reminders(db)
        await db.commit()
    logger.info("Demo dataset seeded successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(seed_demo_data())
