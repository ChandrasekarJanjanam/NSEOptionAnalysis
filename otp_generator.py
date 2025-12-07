import json
from time import sleep
import pyotp


if __name__ == "__main__":

    with open("config.json", "r") as f:
        config = json.load(f)
        zerodha_TOTP_secret = config["zerodha_TOTP_secret"]
        # print(zerodha_TOTP_secret)
        f.close()

    while True:
        # 1) Create or load a Base32 secret (store this securely!)
        # secret = pyotp.random_base32()          # e.g., save to DB or env var

        # 2) Generate current 6-digit TOTP
        totp = pyotp.TOTP(zerodha_TOTP_secret, digits=config["zerodha_TOTP_digits"], interval=config["zerodha_TOTP_interval"])
        code = totp.now()
        print("Current TOTP:", code)

        # 3) Verify a user-entered code (allow small clock drift with 'valid_window')
        user_input = code  # replace with input(...)
        print("Is valid?", totp.verify(user_input, valid_window=1))

        # 4) Optional: provisioning URI for authenticator apps
        # Replace issuer and account name with your app/user identifiers
        uri = totp.provisioning_uri(name="user@example.com", issuer_name="MyApp")
        print("URI:", uri)

        # sleep for 30 secs
        sleep(config["zerodha_TOTP_interval"])



