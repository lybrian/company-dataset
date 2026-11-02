import pytest

from company_dataset.description_rules import acceptable, describes_company


@pytest.mark.parametrize("name,text,ok", [
    ("Generate", "Generate is a leading sustainable infrastructure company that develops, builds, owns, and operates assets.", True),
    ("Karen Clark & Company", "Karen Clark & Company (KCC) is the innovation and technology leader in climate, weather, and catastrophe risk modeling.", True),
    ("COC Consulting", "COC, Continuity of Care, is a leading provider of mobile phlebotomy and imaging services in the US across nine states.", True),
    ("AJS", "AJS are one of the fastest growing and most innovative engineering businesses in the UK, specialising in automation.", True),
    ("Parspec", "Founded in 2021, Parspec is revolutionizing the materials supply chain for the construction industry by digitizing data.", True),
    ("Stellar Health", "At Stellar Health, we help primary care providers put patient health first with a mix of technology and analytics.", True),
    # Long and naming the company, but not saying what it is.
    ("Cometeer", "Capsules can be refrozen if not used immediately. Liquid capsules keep peak flavor for 24 hours. That's why Cometeer is great for travel.", False),
    ("Limelight Steel, Inc.", "Limelight Steel's Laser Furnace named one of the 50 greatest innovations of 2024 by a major technology magazine.", False),
    ("Carolina Complete Health Network", "Carolina Complete Health is providing advanced notice to its provider network of an upcoming update to UM requirements.", False),
    ("RadiantGraph, Inc", "RadiantGraph's platform delivered over 370% improvement in program adoption, with up to 2400% for the best performing cohorts.", False),
    ("Marathon Fusion", "Email us a resume with exactly two bullet points about your most impressive achievements and your interest in Marathon.", False),
    ("Fleetcraft", "News updates: Fleetcraft raises $3.2M to boost aircraft maintenance efficiency with AI, according to a report this week.", False),
    ("equipal", "Location: Hybrid - 8 days per month in office (London) Posted: July 2026 Status: Closed for applications at equipal.", False),
    ("Boam AI", "If these values match your own, Boam AI is a place where you'll feel supported to do your very best work every day.", False),
])
def test_describes_company(name, text, ok):
    assert describes_company(text, name) is ok


@pytest.mark.parametrize("method,text,name,ok", [
    ("board_page_meta", "BECOME A PART OF THE NIMBLE SUCCESS STORY NOW! Great things are happening here at this company every day.", "Nimble Credit Solutions", False),
    ("board_page_meta", "Making happier residents, one community at a time, all across the country and for many years to come.", "KMG Prestige", False),
    ("board_page_meta", "6037 is a venture partnership within the Genesis ecosystem, investing in promising early-stage products.", "6037", True),
    ("careers_page_meta", "We help people grow, and we think that you are going to love it here with all of us every day.", "Acme", False),
    ("homepage_paragraph", "Capsules can be refrozen if not used immediately, which is why Cometeer is a great choice for travel.", "Cometeer", False),
    ("about_page_paragraph", "MAP International is a Christ-centered global health organization guided by a vision of a healthier world.", "MAP International", True),
    # The vendor's own record and a homepage's meta are the company speaking for itself: other rules cover them.
    ("homepage_meta", "Don't settle for cheap swag. We offer remarkable goods branded with your company logo, and much more.", "Clove & Twine", True),
    ("provider_description", "We make great things for great customers, all around the world, every single day of the year.", "Acme", True),
    ("smartrecruiters_company_description", "Founded in Stuttgart in 1886, the group has a unique corporate culture based on trust and responsibility.", "Bosch", True),
    ("job_ad_about_section", "Our team builds tools that many of the largest firms in the world depend on to run every day.", "Acme", True),
])
def test_acceptable_depends_on_where_the_text_came_from(method, text, name, ok):
    assert acceptable(method, text, name) is ok
