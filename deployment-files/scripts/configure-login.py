import json
import base64
import os
import boto3
import sys

# This function takes an 8-digit hexadecimal color string (e.g., 'f2f8fdff')
# and converts it into a 6-digit CSS hexadecimal color string (e.g., '#f2f8fd').
# The last two digits of the 8-digit string typically represent the alpha (opacity)
# value, which is ignored in this conversion for simplicity, assuming full opacity.
# If a 6-digit hex string is provided, it simply prepends a '#' symbol.
def convert_color_to_css_hex(hex_color):
    """Converts an 8-digit hex color string (e.g., 'f2f8fdff') to a 6-digit CSS hex color string (e.g., '#f2f8fd').
    If the input is 6-digits, it prepends '#'. Assumes full opacity if 8 digits.
    """
    if hex_color:
        if len(hex_color) == 8:
            return '#' + hex_color[:6]
        elif len(hex_color) == 6:
            return '#' + hex_color
    return ''

# This function is responsible for generating the custom CSS content.
# It reads various styling properties (like button colors, form background,
# link colors, font family, and border radius) from the `branding_settings`
# dictionary (which is derived from the cognito_full.json file).
# It then constructs a CSS string that uses CSS variables (--amplify-*)
# to define these styles, allowing them to be easily overridden or
# applied to Cognito's hosted UI components. Default values are provided
# if a specific setting is not found in the JSON.
def generate_custom_css(branding_settings):
    """Generates a CSS string based on extracted branding settings from cognito_full.json.
    It attempts to map common Cognito Managed UI CSS variables.
    """
    # Extract relevant color and style properties, providing defaults if not found
    primary_button_bg_default = branding_settings.get('components', {}).get('primaryButton', {}).get('lightMode', {}).get('defaults', {}).get('backgroundColor')
    primary_button_text_default = branding_settings.get('components', {}).get('primaryButton', {}).get('lightMode', {}).get('defaults', {}).get('textColor')
    form_bg_color = branding_settings.get('components', {}).get('form', {}).get('lightMode', {}).get('backgroundColor')
    input_border_color = branding_settings.get('componentClasses', {}).get('input', {}).get('lightMode', {}).get('defaults', {}).get('borderColor')
    link_text_color = branding_settings.get('componentClasses', {}).get('link', {}).get('lightMode', {}).get('defaults', {}).get('textColor')
    button_border_radius = branding_settings.get('componentClasses', {}).get('buttons', {}).get('borderRadius')
    font_family_primary = branding_settings.get('componentClasses', {}).get('body', {}).get('fontFamily')

    # Convert extracted hex colors to CSS hex format
    css_primary_button_bg = convert_color_to_css_hex(primary_button_bg_default)
    css_primary_button_text = convert_color_to_css_hex(primary_button_text_default)
    css_form_bg_color = convert_color_to_css_hex(form_bg_color)
    css_input_border_color = convert_color_to_css_hex(input_border_color)
    css_link_text_color = convert_color_to_css_hex(link_text_color)

    # Construct the CSS content using CSS variables where appropriate
    css_content = f"""
/* Custom CSS generated from cognito_full.json for light mode branding */
/* Note: This CSS attempts to map some common variables. Full replication of */
/* granular component styling may require manual adjustment or using the AWS Console. */

:root {{
  --amplify-primary-button-background-color: {css_primary_button_bg if css_primary_button_bg else '#4f46e5'}; /* Default purple */
  --amplify-primary-button-color: {css_primary_button_text if css_primary_button_text else '#ffffff'}; /* Default white */
  --amplify-form-background-color: {css_form_bg_color if css_form_bg_color else '#ffffff'}; /* Default white */
  --amplify-input-border-color: {css_input_border_color if css_input_border_color else '#cccccc'}; /* Default light grey */
  --amplify-link-color: {css_link_text_color if css_link_text_color else '#0070c9'}; /* Default blue */
  --amplify-border-radius-large: {button_border_radius if button_border_radius else '8'}px; /* Default 8px */
  --amplify-body-font-family: {font_family_primary if font_family_primary else 'sans-serif'}; /* Default sans-serif */
}}

/* Apply general font family to the body */
body {{
    font-family: var(--amplify-body-font-family);
}}

/* Example overrides for common Amplify UI component classes */
/* These class names are indicative and may vary based on Cognito's internal structure */

/* Primary button styling */
.amplify-button[data-variation="primary"],
.button[name="signIn"],
.button[name="signUp"],
.button[name="confirm"] {{
    background-color: var(--amplify-primary-button-background-color) !important;
    color: var(--amplify-primary-button-color) !important;
    border-radius: var(--amplify-border-radius-large) !important;
    border: none !important; /* Ensure no default borders */
    padding: 10px 20px !important; /* Example padding */
    font-weight: bold !important;
    cursor: pointer;
}}

.amplify-button[data-variation="primary"]:hover,
.button[name="signIn"]:hover,
.button[name="signUp"]:hover,
.button[name="confirm"]:hover {{
    filter: brightness(110%); /* Slightly brighter on hover */
}}

/* Form container styling */
.amplify-form,
.auth-form-container {{
    background-color: var(--amplify-form-background-color) !important;
    border-radius: var(--amplify-border-radius-large) !important;
    padding: 20px !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* Subtle shadow */
}}

/* Input field styling */
.amplify-input,
input[type="text"],
input[type="email"],
input[type="password"] {{
    border-color: var(--amplify-input-border-color) !important;
    border-radius: var(--amplify-border-radius-large) !important;
    padding: 10px !important;
    margin-bottom: 15px !important;
    width: calc(100% - 20px) !important; /* Adjust for padding */
}}

/* Link styling */
.amplify-link,
a {{
    color: var(--amplify-link-color) !important;
    text-decoration: none !important;
}}

.amplify-link:hover,
a:hover {{
    text-decoration: underline !important;
}}

/* General text color if needed */
.amplify-text {{
    color: #333333; /* Example default text color */
}}
"""
    return css_content

# This is the main function where the entire workflow is orchestrated.
# It handles command-line arguments, file parsing, AWS client initialization,
# logo handling (decoding and S3 upload), CSS generation and upload, and finally,
# calls the Cognito API to update the User Pool Client Branding.
def main():
    """Main function to parse JSON, upload assets, and update Cognito branding."""
    # Checks if the correct number of command-line arguments are provided.
    # It expects the path to the JSON file, the AWS region, the S3 bucket name, and the environment.
    if len(sys.argv) != 5:
        print("Usage: python configure_cognito_branding.py <path_to_cognito_full_json> <aws_region> <s3_bucket_for_assets> <env>")
        print("Example: python configure_cognito_branding.py ../../cognito_full.json us-east-1 my-cognito-branding-bucket dev")
        sys.exit(1)

    # Assigns command-line arguments to variables for easier access.
    cognito_json_path = sys.argv[1]
    aws_region = sys.argv[2]
    s3_bucket_name = sys.argv[3]
    env = sys.argv[4] # New argument for environment

    print(f"Attempting to configure Cognito Managed Login Branding and App Client settings in region {aws_region}...")
    print(f"Using JSON file: {cognito_json_path}")
    print(f"S3 Bucket for assets: {s3_bucket_name}")
    print(f"Environment: {env}")
    print("-" * 50)

    # Loads and parses the `cognito_full.json` file.
    # It includes error handling for cases where the file is not found
    # or if there's an issue with JSON decoding.
    try:
        with open(cognito_json_path, 'r') as f:
            cognito_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at '{cognito_json_path}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{cognito_json_path}'. Please check file format.")
        sys.exit(1)

    # Extracts crucial information from the parsed JSON, such as
    # User Pool ID, App Client ID, and the Hosted UI Domain.
    # It also extracts the `managedLoginBranding` section, which contains
    # all the detailed branding settings. Error handling is included
    # for missing keys or incorrect indexing.
    try:
        user_pool_id = cognito_data['userPools'][0]['poolId']
        app_client_id = cognito_data['userPools'][0]['clients'][0][0]['clientId']
        hosted_ui_domain = cognito_data['userPools'][0]['hostedUIDomain']['Domain']
        managed_branding = cognito_data['userPools'][0]['managedLoginBranding'][0][0]['managedLoginBranding']
    except (KeyError, IndexError) as e:
        print(f"Error: Missing expected key in JSON structure: {e}")
        print("Please ensure the JSON structure in 'cognito_full.json' matches the expected format.")
        sys.exit(1)

    print(f"✅ Extracted Information:")
    print(f"   User Pool ID:     {user_pool_id}")
    print(f"   App Client ID:    {app_client_id}")
    print(f"   Hosted UI Domain: {hosted_ui_domain}")
    print("-" * 50)

    # Initializes the `boto3` clients for S3, Cognito Identity Provider (cognito-idp),
    # and CloudFormation. This allows the script to interact with AWS services.
    # Error handling is included for issues during client initialization, which
    # might indicate problems with AWS credentials configuration.
    try:
        s3_client = boto3.client('s3', region_name=aws_region)
        cognito_client = boto3.client('cognito-idp', region_name=aws_region)
        cf_client = boto3.client('cloudformation', region_name=aws_region)
    except Exception as e:
        print(f"Error initializing AWS clients. Ensure your AWS credentials are configured: {e}")
        sys.exit(1)

    # --- Determine Redirect URI ---
    # This section aims to dynamically figure out the redirect URI using
    # CloudFormation stack outputs, similar to how update-cognito-callback.sh does.
    # It fetches the S3 bucket name from the CloudFormation stack outputs
    # and constructs the redirect URI based on a predefined path.
    redirect_uri = "" # Initialize as empty string
    s3_stack_name = f"{env}-kashishop-s3"
    print(f"Attempting to determine redirect URI from CloudFormation stack: {s3_stack_name}")
    try:
        response = cf_client.describe_stacks(StackName=s3_stack_name)
        outputs = response['Stacks'][0]['Outputs']
        site_bucket = next(
            (output['OutputValue'] for output in outputs if output['OutputKey'] == 'Kashishop2BucketName'),
            None
        )

        if site_bucket:
            redirect_uri = f"https://{site_bucket}.s3.{aws_region}.amazonaws.com/main/callback.html"
            print(f"   ✓ Redirect URI determined: {redirect_uri}")
        else:
            print(f"   ⚠️ Could not find 'Kashishop2BucketName' output in stack {s3_stack_name}.")
            print("      Redirect URI will remain empty. Please update App Client manually if needed.")
    except Exception as e:
        print(f"   ❌ Error fetching S3 bucket from CloudFormation: {e}")
        print("      Redirect URI will remain empty. Please update App Client manually if needed.")
    print("-" * 50)

    # --- Configure App Client Identity Providers, OAuth Flows, and Scopes ---
    # This crucial section configures the core functionality of the Cognito App Client
    # based on the image provided by the user and common best practices.
    # It sets which identity providers are enabled (e.g., Cognito User Pool itself),
    # which OAuth 2.0 grant types are allowed (e.g., Authorization Code Grant),
    # and which OpenID Connect scopes the application can request (e.g., openid, email).
    print("Configuring App Client Identity Providers, OAuth Flows, and Scopes...")
    try:
        # Define the desired configuration based on the attached image
        # Identity providers: "Cognito user pool"
        supported_identity_providers = ["COGNITO"]

        # OAuth 2.0 grant types: "Authorization code grant"
        allowed_oauth_flows = ["CODE"]

        # OpenID Connect scopes: "OpenID", "Email"
        allowed_oauth_scopes = ["openid", "email"]

        # Set allowed_oauth_flows_user_pool_client to True if using Authorization Code Grant
        # This is typically required when using the Authorization Code Grant
        allowed_oauth_flows_user_pool_client = True

        update_client_params = {
            'UserPoolId': user_pool_id,
            'ClientId': app_client_id,
            'SupportedIdentityProviders': supported_identity_providers,
            'AllowedOAuthFlows': allowed_oauth_flows,
            'AllowedOAuthFlowsUserPoolClient': allowed_oauth_flows_user_pool_client,
            'AllowedOAuthScopes': allowed_oauth_scopes,
            'CallbackURLs': [redirect_uri] if redirect_uri else [], # Only add if determined
            'PreventUserExistenceErrors': 'ENABLED' # Recommended for security
        }

        print("   Parameters for update_user_pool_client:")
        for key, value in update_client_params.items():
            print(f"     {key}: {value}")

        cognito_client.update_user_pool_client(**update_client_params)
        print("   ✅ App Client configuration updated successfully.")
    except Exception as e:
        print(f"   ❌ Error updating App Client configuration: {e}")
        print("      Please ensure the User Pool ID and Client ID are correct,")
        print("      your AWS credentials have sufficient permissions (cognito-idp:UpdateUserPoolClient),")
        print("      and that the Redirect URI is valid if provided.")
    print("-" * 50)


    # This section handles the processing of logos.
    # It decodes base64 encoded logo images (for both light and dark modes)
    # found in the JSON and then uploads them to the specified S3 bucket.
    # Cognito's branding API requires logo URLs from S3, not raw base64 data.
    print("Processing logos...")
    light_logo_s3_url = None
    dark_logo_s3_url = None
    branding_assets = managed_branding.get('Assets', {})

    # Process Light Mode Logo
    if 'lightMode' in branding_assets:
        light_logo_base64 = branding_assets['lightMode'].get('logo')
        if light_logo_base64:
            try:
                # Remove common base64 prefixes (e.g., "data:image/png;base64,")
                if ',' in light_logo_base64:
                    light_logo_base64 = light_logo_base64.split(',', 1)[1] # Split only once

                light_logo_data = base64.b64decode(light_logo_base64)
                # Define a unique key for the S3 object
                light_logo_key = f"cognito-branding/{user_pool_id}/light-logo.png"
                s3_client.put_object(Bucket=s3_bucket_name, Key=light_logo_key, Body=light_logo_data, ContentType='image/png')
                light_logo_s3_url = f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{light_logo_key}"
                print(f"   ✓ Light mode logo uploaded to: {light_logo_s3_url}")
            except Exception as e:
                print(f"   ⚠️ Could not decode or upload light mode logo: {e}")
        else:
            print("   No light mode logo found in JSON.")

    # Process Dark Mode Logo
    if 'darkMode' in branding_assets:
        dark_logo_base64 = branding_assets['darkMode'].get('logo')
        if dark_logo_base64:
            try:
                if ',' in dark_logo_base64:
                    dark_logo_base64 = dark_logo_base64.split(',', 1)[1]

                dark_logo_data = base64.b64decode(dark_logo_base64)
                dark_logo_key = f"cognito-branding/{user_pool_id}/dark-logo.png"
                s3_client.put_object(Bucket=s3_bucket_name, Key=dark_logo_key, Body=dark_logo_data, ContentType='image/png')
                dark_logo_s3_url = f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{dark_logo_key}"
                print(f"   ✓ Dark mode logo uploaded to: {dark_logo_s3_url}")
            except Exception as e:
                print(f"   ⚠️ Could not decode or upload dark mode logo: {e}")
        else:
            print("   No dark mode logo found in JSON.")
    print("-" * 50)

    # This section generates the custom CSS content using the `generate_custom_css`
    # function and then uploads this CSS file to the specified S3 bucket.
    # This CSS file will be referenced by Cognito to apply custom styles to the
    # hosted UI.
    print("Generating and uploading custom CSS...")
    custom_css_content = generate_custom_css(managed_branding.get('Settings', {}))
    css_file_key = f"cognito-branding/{user_pool_id}/custom-styles.css"
    try:
        s3_client.put_object(Bucket=s3_bucket_name, Key=css_file_key, Body=custom_css_content.encode('utf-8'), ContentType='text/css')
        custom_css_s3_url = f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{css_file_key}"
        print(f"   ✓ Custom CSS uploaded to: {custom_css_s3_url}")
        print("\n--- Generated CSS Content ---")
        print(custom_css_content)
        print("-----------------------------\n")
    except Exception as e:
        print(f"   ❌ Error uploading custom CSS to S3: {e}")
        custom_css_s3_url = None
    print("-" * 50)

    # This is the final step, where the script calls the `update_user_pool_client_branding`
    # API of Cognito using `boto3`. It passes the S3 URLs for the light mode logo,
    # dark mode logo, and the custom CSS file. This action applies the branding
    # changes to your Cognito User Pool's hosted UI.
    print("Updating User Pool Client Branding...")
    try:
        update_params = {
            'UserPoolId': user_pool_id,
            'ClientId': app_client_id,
        }
        if light_logo_s3_url:
            update_params['LightModeLogo'] = light_logo_s3_url
        if dark_logo_s3_url:
            update_params['DarkModeLogo'] = dark_logo_s3_url
        if custom_css_s3_url:
            update_params['Css'] = custom_css_s3_url

        # Perform the update
        cognito_client.update_user_pool_client_branding(**update_params)
        print("   ✅ User Pool Client Branding update initiated successfully.")
        print("      Note: Changes might take a few moments to propagate across Cognito's hosted UI.")
    except Exception as e:
        print(f"   ❌ Error updating User Pool Client Branding: {e}")
        print("      Please check AWS permissions and ensure the User Pool and Client IDs are correct.")
    print("-" * 50)

    # Prints the final Hosted UI login URL, which can be used to verify the
    # applied branding changes. The dynamically determined redirect URI is included.
    print("\nFinal Hosted UI Login URL (for testing):")
    print(f"https://{hosted_ui_domain}.auth.{aws_region}.amazoncognito.com/login?response_type=code&client_id={app_client_id}&redirect_uri={redirect_uri}")
    print("If the redirect URI is a placeholder, ensure your CloudFormation stack 'Kashishop2BucketName' output is available.")

# Ensures that the `main` function is called only when the script is executed directly.
if __name__ == '__main__':
    main()
