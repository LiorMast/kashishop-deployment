#!/usr/bin/env python3

import json
import base64
import os
import boto3
import sys
import subprocess
import random

def convert_color_to_css_hex(hex_color):
    if hex_color:
        if len(hex_color) == 8:
            return '#' + hex_color[:6]
        elif len(hex_color) == 6:
            return '#' + hex_color
    return ''

def generate_custom_css(branding_settings):
    primary_button_bg = branding_settings.get('components', {}) \
        .get('primaryButton', {}).get('lightMode', {}) \
        .get('defaults', {}).get('backgroundColor')
    primary_button_text = branding_settings.get('components', {}) \
        .get('primaryButton', {}).get('lightMode', {}) \
        .get('defaults', {}).get('textColor')
    link_text_color = branding_settings.get('componentClasses', {}) \
        .get('link', {}).get('lightMode', {}) \
        .get('defaults', {}).get('textColor')
    button_radius = branding_settings.get('componentClasses', {}) \
        .get('buttons', {}).get('borderRadius')
    font_family = branding_settings.get('componentClasses', {}) \
        .get('body', {}).get('fontFamily')

    css = {
        'primary_bg': convert_color_to_css_hex(primary_button_bg) or '#4f46e5',
        'primary_text': convert_color_to_css_hex(primary_button_text) or '#ffffff',
        'link_color': convert_color_to_css_hex(link_text_color) or '#0070c9',
        'radius': f"{button_radius or 8}px"
    }
    css['form_bg'] = '#' + ''.join(random.choice('0123456789ABCDEF') for _ in range(6))

    return f"""
:root {{
  --amplify-primary-button-background-color: {css['primary_bg']};
  --amplify-primary-button-color: {css['primary_text']};
  --amplify-form-background-color: {css['form_bg']};
  --amplify-input-border-color: #cccccc;
  --amplify-link-color: {css['link_color']};
  --amplify-border-radius-large: {css['radius']};
  --amplify-body-font-family: {font_family or 'sans-serif'};
}}
body {{ font-family: var(--amplify-body-font-family); }}
.amplify-button[data-variation="primary"], .button[name="signIn"], .button[name="signUp"], .button[name="confirm"] {{
    background-color: var(--amplify-primary-button-background-color) !important;
    color: var(--amplify-primary-button-color) !important;
    border-radius: var(--amplify-border-radius-large) !important;
    border: none !important;
    padding: 10px 20px !important;
    font-weight: bold !important;
    cursor: pointer;
}}
.amplify-button[data-variation="primary"]:hover, .button[name="signIn"]:hover, .button[name="signUp"]:hover, .button[name="confirm"]:hover {{
    filter: brightness(110%);
}}
.amplify-form, .auth-form-container {{
    background-color: var(--amplify-form-background-color) !important;
    border-radius: var(--amplify-border-radius-large) !important;
    padding: 20px !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}}
.amplify-input, input[type="text"], input[type="email"], input[type="password"] {{
    border-color: var(--amplify-input-border-color) !important;
    border-radius: var(--amplify-border-radius-large) !important;
    padding: 10px !important;
    margin-bottom: 15px !important;
    width: calc(100% - 20px) !important;
}}
.amplify-link, a {{ color: var(--amplify-link-color) !important; text-decoration: none !important; }}
.amplify-link:hover, a:hover {{ text-decoration: underline !important; }}
.amplify-text {{ color: #333333; }}
"""

def aws_cli_query(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running AWS CLI {' '.join(cmd)}: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) != 5:
        print("Usage: python configure-login.py <path_to_cognito_full.json> <aws_region> <s3_bucket_for_assets> <env>")
        sys.exit(1)

    json_path, aws_region, s3_bucket, env = sys.argv[1:]

    try:
        with open(json_path) as f:
            cognito_data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON: {e}", file=sys.stderr)
        sys.exit(1)

    cf_stack = f"{env}-kashishop-cognito"
    user_pool_id = aws_cli_query([
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", cf_stack,
        "--region", aws_region,
        "--query", "Stacks[0].Outputs[?OutputKey=='KashishopUserPoolId'].OutputValue",
        "--output", "text"
    ])
    app_client_id = aws_cli_query([
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", cf_stack,
        "--region", aws_region,
        "--query", "Stacks[0].Outputs[?OutputKey=='Kashishop2UserPoolClientId'].OutputValue",
        "--output", "text"
    ])

    try:
        hosted_ui_domain = cognito_data['userPools'][0]['hostedUIDomain']['Domain']
    except (KeyError, IndexError):
        hosted_ui_domain = None

    print(f"Using AWS region {aws_region}")
    print(f"User Pool ID: {user_pool_id}")
    print(f"App Client ID: {app_client_id}")
    if hosted_ui_domain:
        print(f"Hosted UI Domain: {hosted_ui_domain}")
    print("-" * 50)

    redirect_uri = f"https://{s3_bucket}.s3.{aws_region}.amazonaws.com/main/callback.html"

    cognito = boto3.client('cognito-idp', region_name=aws_region)
    params = {
        'UserPoolId': user_pool_id,
        'ClientId': app_client_id,
        'SupportedIdentityProviders': ["COGNITO"],
        'AllowedOAuthFlows': ["code"],
        'AllowedOAuthFlowsUserPoolClient': True,
        'AllowedOAuthScopes': ["openid", "email"],
        'CallbackURLs': [redirect_uri],
        'LogoutURLs': [redirect_uri],
        'PreventUserExistenceErrors': 'ENABLED'
    }

    print("Updating user pool client settings…")
    cognito.update_user_pool_client(**params)
    print("✅ App Client configuration updated.")
    print("-" * 50)

    final_url = (
        f"https://{env}-{hosted_ui_domain}.auth.{aws_region}.amazoncognito.com/"
        f"login?client_id={app_client_id}&response_type=code&scope=email+openid"
        f"&redirect_uri={redirect_uri}"
    )

    print("\nFinal Hosted UI Login URL (for testing):")
    print(final_url)
    return final_url

if __name__ == '__main__':
    login_url = main()
    script_dir = os.path.dirname(__file__)
    updater = os.path.join(script_dir, 'update-login-button.py')
    try:
        subprocess.run(['python3', updater, login_url], check=True)
        print("✅ Login button updated successfully.")
    except Exception as e:
        print(f"⚠️ Failed to update Login button: {e}", file=sys.stderr)
        sys.exit(1)
