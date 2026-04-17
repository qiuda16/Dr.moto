from reportlab.pdfgen import canvas
import os

def create_dummy_manual():
    filename = "Ducati_Monster_Manual_Mock.pdf"
    c = canvas.Canvas(filename)
    
    # Page 1: Cover
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, 700, "OFFICIAL MAINTENANCE MANUAL")
    c.drawString(100, 650, "MODEL: DUCATI MONSTER 937")
    c.showPage()
    
    # Page 2: Oil Change
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, "SECTION 1: OIL CHANGE PROCEDURE")
    c.setFont("Helvetica", 12)
    text = """
    1. Warm up the engine for 5 minutes.
    2. Remove the drain plug (12mm hex) located at the bottom left.
    3. Allow oil to drain for at least 15 minutes.
    4. Replace the oil filter (Part No. 444.4.003.5A).
    5. Fill with 3.2 Liters of Shell Advance 15W-50.
    6. Torque the drain plug to 20 Nm.
    WARNING: Do not overfill. Check sight glass level.
    """
    y = 750
    for line in text.split('\n'):
        c.drawString(50, y, line.strip())
        y -= 20
    c.showPage()
    
    # Page 3: Chain Tension
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, "SECTION 2: CHAIN TENSION")
    c.setFont("Helvetica", 12)
    text2 = """
    The chain tension must be checked with the bike on the side stand.
    The correct slack is 28-30 mm at the midpoint of the swingarm.
    To adjust:
    1. Loosen the rear axle nut (30mm).
    2. Turn the adjuster bolts equally on both sides.
    3. Ensure alignment marks match.
    4. Torque rear axle nut to 145 Nm.
    """
    y = 750
    for line in text2.split('\n'):
        c.drawString(50, y, line.strip())
        y -= 20
        
    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_dummy_manual()
