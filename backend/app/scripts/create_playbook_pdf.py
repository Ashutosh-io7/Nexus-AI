"""Generates the official Nexus Corporate Retention Playbook PDF."""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
OUTPUT_PDF = DATA_DIR / "retention_playbook.pdf"


def generate_pdf():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT_PDF), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0e5f66"),
        spaceAfter=15,
    )
    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#101828"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#344054"),
        spaceAfter=8,
    )

    story = [
        Paragraph("Nexus AI — Customer Success Standard Operating Procedures", title_style),
        Paragraph("<b>Document Title:</b> Global Retention, Downgrade & Save Authority Guidelines", body_style),
        Paragraph("<b>Version:</b> 2.4 (Enterprise Production)", body_style),
        Paragraph("<b>Scope:</b> Applies to all Customer Success Managers, Account Executives, and Support Leads.", body_style),
        Spacer(1, 15),

        Paragraph("Section 1: Churn Risk Tiers & Mandatory SLAs", h1_style),
        Paragraph("• <b>Low Risk (&lt; 30% Churn Probability):</b> Accounts in this tier require standard proactive nurture. Quarterly product webinars and automated satisfaction surveys are scheduled automatically. No discount authorization is permitted without expansion.", body_style),
        Paragraph("• <b>Medium Risk (30% to 50% Churn Probability):</b> The Customer Success Manager must initiate an account audit within 5 business days. Review recent usage drop-offs and offer a complimentary 30-minute workflow optimization call.", body_style),
        Paragraph("• <b>High Risk (&gt; 50% Churn Probability):</b> Triggers an urgent 48-hour response protocol. A senior CSM must conduct an immediate stakeholder review, verify billing contact validity, and schedule executive outreach.", body_style),
        Spacer(1, 10),

        Paragraph("Section 2: Pricing Authority & Maximum Allowed Discounts", h1_style),
        Paragraph("• <b>Month-to-Month Save Strategy:</b> To stabilize accounts on flexible monthly contracts, CSMs are pre-authorized to offer up to a 10% discount for 3 months, provided the customer transitions to an agreed 6-month contract commitment.", body_style),
        Paragraph("• <b>High-Value Accounts (MRR &gt; $100 or Tenure &gt; 12 Months):</b> Authorized for up to a 15% discount for 6 months or 1 month free credit in exchange for an annual (12-month) commitment.", body_style),
        Paragraph("• <b>Enterprise Exception Tier:</b> Up to 20% discount on annual commitments. Requires written approval from the VP of Customer Success.", body_style),
        Paragraph("• <b>Strict Prohibitions:</b> Under no circumstances may any representative authorize discounts exceeding 20%, provide indefinite free credits, or waive unpaid historical balances without finance approval.", body_style),
        PageBreak(),

        Paragraph("Section 3: Contract Restructuring & Flexibility Rules", h1_style),
        Paragraph("• <b>Seasonal & Financial Hardship Pauses:</b> Accounts in good standing may pause their active subscription billing for up to 60 calendar days without losing customer configuration, analytics, or historical records.", body_style),
        Paragraph("• <b>Downsizing & Tier Downgrades:</b> When a customer requests cancellation citing team contraction or budget reductions, reps must offer a downgrade to the next lower tier (e.g., Enterprise to Pro) with contract restatement, explicitly waiving early termination fees.", body_style),
        Paragraph("• <b>Billing Frequency Conversion:</b> Transitioning from monthly to annual prepaid billing provides 2 months free (equivalent to 16.6% annual savings) without requiring VP approval.", body_style),
        Spacer(1, 10),

        Paragraph("Section 4: Technical Friction & Support Escalation Remedies", h1_style),
        Paragraph("• <b>Unresolved Support Tickets & SLA Breaches:</b> If a customer has unresolved high-priority tickets open for more than 7 days, assign a dedicated Solutions Architect for a direct technical review call and issue a 1-month 50% service credit.", body_style),
        Paragraph("• <b>Consecutive Payment Failures:</b> For accounts with 2 or more consecutive payment failures, verify credit card expiration and offer automated ACH or invoice terms with Net-30 payment buffers before service suspension.", body_style),
        Paragraph("• <b>Platform Latency & Outage Complaints:</b> Offer priority support routing and assign direct phone-support escalation for the following 90 days.", body_style),
        Spacer(1, 10),

        Paragraph("Section 5: Feature Adoption & Engagement Drop Interventions", h1_style),
        Paragraph("• <b>Usage Drop (&gt; 25% Decline in 30 Days):</b> Schedule a 1-on-1 feature re-alignment session to identify bottlenecks. Provide customized Loom tutorials for underutilized modules.", body_style),
        Paragraph("• <b>Executive Champion Departure:</b> If the primary sponsor leaves the customer's organization, initiate a new stakeholder discovery session within 7 calendar days to train the incoming team lead.", body_style),
    ]

    doc.build(story)
    print(f"Generated official Retention Playbook PDF at: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()