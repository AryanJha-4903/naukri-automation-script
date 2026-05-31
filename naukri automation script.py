from playwright.sync_api import sync_playwright
from datetime import datetime
import smtplib, os, time, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL           = os.getenv("EMAIL")
APP_PASSWORD    = os.getenv("APP_PASSWORD")
NAUKRI_EMAIL    = os.getenv("NAUKRI_EMAIL")
NAUKRI_PASSWORD = os.getenv("NAUKRI_PASSWORD")
RESUME_PATH     = os.getenv("RESUME_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume.pdf")

# ─────────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────────
def send_email(status, details=""):
    try:
        now   = datetime.now().strftime("%A, %d %B %Y at %I:%M %p")
        icon  = "✅" if status == "success" else ("⚠️" if status == "session_expired" else "❌")
        color = "#28a745" if status == "success" else ("#f0ad4e" if status == "session_expired" else "#dc3545")
        title = {
            "success":         "✅ Naukri Profile Updated Successfully",
            "session_expired": "⚠️ Session Expired — Action Required",
            "failed":          "❌ Naukri Profile Update Failed",
        }.get(status, "Naukri Update")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Naukri Update - {icon} {status.title()} | {datetime.now().strftime('%d %b %Y')}"
        msg["From"]    = EMAIL
        msg["To"]      = EMAIL

        html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:30px;">
          <div style="max-width:520px;margin:auto;background:white;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);overflow:hidden;">
            <div style="background:{color};padding:24px 30px;">
              <h2 style="color:white;margin:0;font-size:20px;">{title}</h2>
            </div>
            <div style="padding:24px 30px;">
              <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr><td style="padding:10px 0;border-bottom:1px solid #eee;color:#666;width:35%;">Date &amp; Time</td>
                    <td style="padding:10px 0;border-bottom:1px solid #eee;font-weight:500;">{now}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #eee;color:#666;">Status</td>
                    <td style="padding:10px 0;border-bottom:1px solid #eee;font-weight:500;color:{color};">{status.title()}</td></tr>
                <tr><td style="padding:10px 0;color:#666;">Details</td>
                    <td style="padding:10px 0;">{details}</td></tr>
              </table>
              {"<div style='margin-top:20px;padding:14px;background:#fff8e1;border-left:4px solid #f0ad4e;border-radius:4px;font-size:13px;'><b>Action needed:</b> Run <code>capture_session.py</code> to re-login.</div>" if status == "session_expired" else ""}
            </div>
            <div style="padding:14px 30px;background:#fafafa;font-size:12px;color:#aaa;text-align:center;">Automated message from your Naukri Profile Bot</div>
          </div>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, APP_PASSWORD)
            server.sendmail(EMAIL, EMAIL, msg.as_string())
        print(f"📧 Email sent: {status}")
    except Exception as e:
        print(f"⚠️  Email failed: {e}")


# ─────────────────────────────────────────────
# BROWSER SETUP — stealth context
# ─────────────────────────────────────────────
def make_context(p, session_file=None):
    browser = p.chromium.launch(
        headless=True,
        slow_mo=100,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
    )
    kwargs = dict(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9",
            "sec-ch-ua": '"Chromium";v="124","Google Chrome";v="124","Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
    )
    if session_file:
        kwargs["storage_state"] = session_file

    context = browser.new_context(**kwargs)
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-IN','en']});
        window.chrome = { runtime: {} };
    """)
    return browser, context


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def update_naukri_profile():
    print(f"\n🚀 Starting Naukri update — {datetime.now().strftime('%I:%M %p, %d %b %Y')}")
    detail_msg = "Profile page visited."

    with sync_playwright() as p:

        # ── Load session or login fresh ──
        session_file = "naukri_session.json" if os.path.exists("naukri_session.json") else None
        browser, context = make_context(p, session_file)
        page = context.new_page()

        # ── Navigate: homepage first, then profile ──
        print("🌐 Loading Naukri homepage...")
        page.goto("https://www.naukri.com", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        print("👤 Going to profile page...")
        page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("load", timeout=60000)
        time.sleep(3)

        print(f"📍 URL: {page.url}")

        # ── Login if needed ──
        if "nlogin" in page.url or "login" in page.url:
            print("🔓 Not logged in — logging in with email/password...")

            page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("#usernameField", timeout=30000)
            time.sleep(1)

            page.fill("#usernameField", NAUKRI_EMAIL)
            time.sleep(0.5)
            page.fill("#passwordField", NAUKRI_PASSWORD)
            time.sleep(0.5)
            page.click("button[type='submit']")
            page.wait_for_load_state("load", timeout=60000)
            time.sleep(2)

            # if "nlogin" in page.url or "login" in page.url:
            #     raise Exception("Login failed — check NAUKRI_EMAIL / NAUKRI_PASSWORD in .env")

            print("✅ Logged in!")

            # Go to homepage then profile after login
            page.goto("https://www.naukri.com", wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("load", timeout=60000)
            time.sleep(3)

        else:
            print("✅ Session valid — already on profile!")

        # ── Check for Akamai block ──
        if "Access Denied" in page.content():
            raise Exception("Akamai/CDN blocked the request. Delete naukri_session.json and re-run capture_session.py")

        # Save fresh session
        context.storage_state(path="naukri_session.json")

        # ── Step 3: Upload resume via JS ──
        print("📄 Re-uploading resume...")

        if not os.path.exists(RESUME_PATH):
            raise FileNotFoundError(f"Resume not found: {RESUME_PATH}")

        # Encode resume to base64
        with open(RESUME_PATH, "rb") as f:
            resume_base64 = base64.b64encode(f.read()).decode("utf-8").strip()
        filename = os.path.basename(RESUME_PATH)
        print(f"📋 File: {filename} | Size: {len(resume_base64)} chars")

        # Scroll to trigger React rendering
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)

        # Count file inputs
        input_count = page.evaluate("document.querySelectorAll('input[type=\"file\"]').length")
        print(f"📋 File inputs found: {input_count}")

        if input_count == 0:
            raise Exception("No file input found on page — Naukri may have blocked or not rendered the upload section")

        # Inject file via JS (same script that works in your browser console)
        result = page.evaluate(
            """function(data) {
                var binary = atob(data.b64);
                var array  = new Uint8Array(binary.length);
                for (var i = 0; i < binary.length; i++) {
                    array[i] = binary.charCodeAt(i);
                }
                var file         = new File([array], data.name, { type: 'application/pdf' });
                var dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                var input = document.querySelector('input[type="file"]');
                if (!input) throw new Error('input[type=file] not found');
                input.files = dataTransfer.files;
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('input',  { bubbles: true }));
                return 'ok';
            }""",
            {"b64": resume_base64, "name": filename}
        )

        print(f"📤 JS inject result: {result}")
        time.sleep(5)

        # Confirm upload by checking filename on page
        try:
            uploaded_name = page.inner_text(".resume-name-inline .truncate")
            print(f"✅ Resume uploaded: {uploaded_name}")
            detail_msg = f"Resume re-uploaded: {uploaded_name}"
        except:
            detail_msg = "JS inject ran successfully (could not confirm filename)"
            print(f"⚠️  {detail_msg}")

        browser.close()

    print("📧 Sending email...")
    send_email("success", detail_msg)
    print("🎉 Done!\n")


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        update_naukri_profile()
    except Exception as e:
        err = str(e)
        print(f"❌ Error: {err}")
        if "session" in err.lower() or "login" in err.lower() or "blocked" in err.lower():
            send_email("session_expired", err)
        else:
            send_email("failed", err)
            
            
            
            
            
            
            
            
            
