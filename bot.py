import discord
from discord.ext import commands, tasks
import json
import os
import requests
from datetime import datetime
import math
import asyncio
import aiohttp


# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# File to store user data
# DATA_FILE =  "/data/data/com.termux/files/home/Warbot/user_data.json"
# WAR_DATA_FILE = "/data/data/com.termux/files/home/Warbot/war_data.json"
# TRACKING_FILE = "/data/data/com.termux/files/home/Warbot/tracking.json"
# NOTIFIED_FILE = "/data/data/com.termux/files/home/Warbot/notified.json"
TRACKING_FILE = r"C:\Users\Vishnu Gupta\Desktop\Testing\tracking.json"
NOTIFIED_FILE = r"C:\Users\Vishnu Gupta\Desktop\Testing\notified.json"
WAR_DATA_FILE = r"C:\Users\Vishnu Gupta\Desktop\Testing\war_data.json"
DATA_FILE = r"C:\Users\Vishnu Gupta\Desktop\Testing\user_data.json"


print(f"Looking for user_data.json in: {os.getcwd()}")


# Ensure the file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as file:
        json.dump({}, file)

# Load user data
def load_data(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        with open(file_path, "w") as file:
            json.dump({}, file, indent=4)
        return {}


# Save user data
def save_data(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

# Command to import data
@bot.command()
@commands.has_permissions(administrator=True)  # Restrict to admins
async def import_data(ctx, *, raw_data: str):
    """
    Import bulk user data into user_data.json.
    Command expects raw JSON data as input.
    Example: !import_data {"user_id": nation_id, ...}
    """
    try:
        # Parse the raw JSON input
        new_data = json.loads(raw_data)

        if not isinstance(new_data, dict):
            await ctx.send("Invalid format. Please provide a valid JSON object.")
            return

        # Load existing data
        current_data = load_data(DATA_FILE)

        # Merge the new data with existing data
        current_data.update(new_data)

        # Save back to the file
        save_data(DATA_FILE,current_data)

        await ctx.send("✅ Data successfully imported and saved!")
    except json.JSONDecodeError:
        await ctx.send("❌ Failed to parse JSON. Please ensure the data is correctly formatted.")

@bot.command()
@commands.has_permissions(administrator=True)  # Restrict to admins
async def get_all_data(ctx):
    """
    Command to retrieve all user data stored in user_data.json.
    """
    try:
        data = load_data(DATA_FILE)  # Load the data from the JSON file

        if not data:
            await ctx.send("The user data file is currently empty.")
            return

        # Convert data to a formatted JSON string
        formatted_data = json.dumps(data, indent=4)

        # Send the data as a file for better readability
        file_path = "user_data_dump.json"
        with open(file_path, "w") as file:
            file.write(formatted_data)

        await ctx.send("📂 Here is the current user data:", file=discord.File(file_path))

    except Exception as e:
        await ctx.send("❌ Failed to retrieve the user data. Please check the logs.")
        print(f"Error retrieving user data: {e}")



# Command to register a user
@bot.command()
async def register(ctx, nation_id: int):
    user_id = str(ctx.author.id)
    data = load_data(DATA_FILE)
    
    if user_id in data:
        await ctx.send(f"You are already registered with nation ID {data[user_id]}.")
    else:
        data[user_id] = nation_id
        save_data(DATA_FILE,data)
        await ctx.send(f"Successfully registered with nation ID {nation_id}!")

# Command to update nation ID
@bot.command()
async def update_nation(ctx, new_id: int):
    user_id = str(ctx.author.id)
    data = load_data(DATA_FILE)

    if user_id in data:
        data[user_id] = new_id
        save_data(DATA_FILE,data)
        await ctx.send(f"Your nation ID has been updated to {new_id}.")
    else:
        await ctx.send("You are not registered. Use `!register` to register.")

# Command to delete registration
@bot.command()
async def delete_registration(ctx):
    user_id = str(ctx.author.id)
    data = load_data(DATA_FILE)

    if user_id in data:
        del data[user_id]
        save_data(DATA_FILE,data)
        await ctx.send("Your registration has been deleted.")
    else:
        await ctx.send("You are not registered. Use `!register` to register.")

# Command to manually register someone
@bot.command()
@commands.has_any_role("Helpers", "War Assisters", "Coordinator of Counters")
async def manual_register(ctx, member: discord.Member, nation_id: int):
    user_id = str(member.id)
    data = load_data(DATA_FILE)

    if user_id in data:
        await ctx.send(f"{member.mention} is already registered with nation ID {data[user_id]}.")
    else:
        data[user_id] = nation_id
        save_data(DATA_FILE,data)
        await ctx.send(f"Successfully registered {member.mention} with nation ID {nation_id}!")

# Error handler for missing permissions
@manual_register.error
async def manual_register_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("You do not have permission to use this command.")

# Command to show the nation ID
@bot.command()
async def show_nation(ctx):
    user_id = str(ctx.author.id)
    data = load_data(DATA_FILE)

    if user_id in data:
        await ctx.send(f"Your nation ID is {data[user_id]}.")
    else:
        await ctx.send("You are not registered. Use `!register` to register.")


# !who command to fetch nation details
@bot.command()
async def who(ctx, member: discord.Member):
    user_id = str(member.id)
    data = load_data(DATA_FILE)

    if user_id not in data:
        await ctx.send(f"{member.mention} is not registered.")
        return

    nation_id = data[user_id]
    api_url = f"https://diplomacyandstrifeapi.com/api/nation?APICode=f1240165d97856f&NationId={nation_id}"

    # Call the API
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for HTTP issues
        nation_data = response.json()[0]  # Extract the first element of the JSON array
    except Exception as e:
        await ctx.send("Failed to fetch data from the API. Please try again later.")
        print(f"API Error: {e}")
        return

    # Prepare the data
    nation_name = nation_data.get("NationName", "Unknown")
    alliance = nation_data.get("Alliance", "None")
    score = nation_data.get("Score", "Unknown")
    cash_output = nation_data.get("CashOutput", 0)
    mineral_output = nation_data.get("MineralOutput", 0)
    production_output = nation_data.get("ProductionOutput", 0)
    fuel_output = nation_data.get("FuelOutput", 0)
    uranium_output = nation_data.get("UraniumOutput", 0)
    rare_metal_output = nation_data.get("RareMetalOutput", 0)
    political_power_output = nation_data.get("PoliticalPowerOutput", 0)
    off_wars = nation_data.get("OffWars", 0)
    def_wars = nation_data.get("DefWars", 0)
    dev = nation_data.get("Infra",0)
    ncl = nation_data.get("NonCoreLand",0)
    cl = nation_data.get("CoreLand",0)

    # Create a message with no embeds
    response_message = (
        f"**Nation Name**: {nation_name} (<https://diplomacyandstrife.com/nation/{nation_id}>)\n"
        f"**Alliance**: {alliance}\n"
        f"`Dev:{dev:,}` `Core Land:{cl:,}` `Non Core Land:{ncl:,}`\n"
        f"   - **Outputs**:\n"
        f"   - **Cash**: {cash_output:,}\n"
        f"   - **Minerals**: {mineral_output:,}\n"
        f"   - **Production**: {production_output:,}\n"
        f"   - **Fuel**: {fuel_output:,}\n"
        f"   - **Uranium**: {uranium_output:,}\n"
        f"   - **Rare Metals**: {rare_metal_output:,}\n"
        f"   - **Political Power**: {political_power_output}\n"
        f"----------------------------------\n"
        f"**Score**: {score:,}\n"
        f"`OffWars⚔️: {off_wars}/5`\n"
        f"`DefWars🛡️: {def_wars}/2`\n"
    )

    await ctx.send(response_message)

def has_permission(ctx, mention_id):
    """
    Check if the command invoker has permission to view the stockpile.
    Permissions: Helpers, War Assisters, Admins, or the owner of the nation.
    """
    if any(role.name in ["Helpers", "War Assisters", "Coordinator of Counters"] for role in ctx.author.roles):
        return True
    
    # Only allow the user to view their own stockpile
    if str(mention_id) == str(ctx.author.id):
        return True
    
    return False

# Command to fetch and display the stockpile
@bot.command()
async def stockpile(ctx, mention: discord.Member):
    user_id = str(ctx.author.id)
    data = load_data(DATA_FILE)
    
    # Check if the mentioned user has a nation ID
    if str(mention.id) not in data:
        await ctx.send(f"{mention.mention} is not registered.")
        return

    nation_id = data[str(mention.id)]

    # Check if the user has permission to view this stockpile
    if not has_permission(ctx, mention.id):
        await ctx.send("You do not have permission to check this user's stockpile.")
        return
    
    # Fetch stockpile data from the API
    api_url = f"https://diplomacyandstrifeapi.com/api/AllianceMemberInventory?APICode=f1240165d97856f&NationId={nation_id}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for HTTP issues
        data = response.json()
    except Exception as e:
        await ctx.send(f"Error fetching data for {mention.mention}: {e}")
        return

    # Calculate stockpile (total quantity, average quality)
    stockpile = calculate_stockpile(data)

    # Prepare the response message with the requested format
    response_message = "**Nation Inventory Stockpile**\n"

    # List of item types to display in the specified order
    item_types_order = [
        "Infantry Equipment", "Support Vehicles", "Artillery", "Missile Launchers",
        "Light Tanks", "Medium Tanks", "Heavy Tanks", "Light Mechs", "Heavy Mechs", 
        "Prescours Mechs", "Fighters", "Stealth Fighters", "Destroyers", "Submarines", 
        "Cruisers", "Battleships", "Carriers"
    ]
    
    # Add data to the response in the required order
    for item_type in item_types_order:
        if item_type in stockpile:
            total_quantity = stockpile[item_type]["total_quantity"]
            average_quality = stockpile[item_type]["average_quality"]
            response_message += f"{item_type} - Total Quantity: {total_quantity:,} (Quality: {average_quality})\n"
        else:
            response_message += f"{item_type} - Total Quantity: 0 (Quality: 0)\n"
    
    # Send the formatted message
    await ctx.send(f"```\n{response_message}```")

# Function to calculate stockpile data (sum quantity and average quality)
def calculate_stockpile(data):
    """
    Calculate the total quantity and average quality for each item type from the stockpile data.
    """
    stockpile = {}

    # Iterate through all items in the API data
    for item in data:
        item_type = item["type"]
        quality = item["quality"]
        quantity = item["quantity"]

        if item_type not in stockpile:
            stockpile[item_type] = {"total_quantity": 0, "total_quality": 0, "count": 0}

        # Sum the quantities
        stockpile[item_type]["total_quantity"] += quantity
        # Calculate the weighted total quality
        stockpile[item_type]["total_quality"] += quality * quantity
        # Count the total quantity for averaging
        stockpile[item_type]["count"] += quantity

    # Calculate the average quality for each item type
    for item_type, values in stockpile.items():
        if values["count"] > 0:
            average_quality = values["total_quality"] / values["count"]
        else:
            average_quality = 0

        # Round the average quality to 2 decimal places
        values["average_quality"] = round(average_quality, 2)

    return stockpile


def has_permission(ctx, mention_id):
    """
    Check if the command invoker has permission to view the stockpile.
    Permissions: Helpers, War Assisters, Admins, or the owner of the nation.
    """
    if any(role.name in ["Helpers", "War Assisters", "Coordinator of Counters"] for role in ctx.author.roles):
        return True
    
    # Only allow the user to view their own stockpile
    if str(mention_id) == str(ctx.author.id):
        return True
    
    return False

@bot.command()
async def tech(ctx, mention: discord.Member):
    # Load user data to find the nation ID
    user_data = load_data(DATA_FILE)
    
    # Get the nation_id for the mentioned user (mention.id)
    mentioned_user_id = str(mention.id)  # Convert to string because JSON keys are usually strings
    if mentioned_user_id not in user_data:
        await ctx.send(f"{mention.mention} does not have a registered nation ID.")
        return

    nation_id = user_data[mentioned_user_id]

    # Fetch technology data from the API using the nation_id
    api_url = "https://diplomacyandstrifeapi.com/api/AllianceTech?APICode=f1240165d97856f"
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for HTTP issues
        tech_data = response.json()
    except Exception as e:
        await ctx.send(f"Error fetching technology data: {e}")
        return

    # Find the technology data for the mentioned user's nation_id
    mentioned_nation_id = None
    for nation in tech_data:
        if nation["nationID"] == nation_id:  # Match the nationID of the mentioned user
            mentioned_nation_id = nation
            break

    if not mentioned_nation_id:
        await ctx.send(f"Could not find technology data for nation ID {nation_id}.")
        return

    # Extract and format the requested technology data
    tech_info = {
        "Espionage": mentioned_nation_id["Espionage"],
        "Counter Intelligence": mentioned_nation_id["CounterIntelligence"],
        "Cyber Defense": mentioned_nation_id["CyberDefense"],
        "Electronic Warfare": mentioned_nation_id["ElectronicWarfare"]
    }

    # Prepare the response message
    response_message = f"Technology Data\n"
    for tech, value in tech_info.items():
        response_message += f"{tech}: {value}\n"

    # Send the technology data as a message
    await ctx.send(f"```\n{response_message}```")


def fetch_nation_data(nation_id):
    url = f'https://diplomacyandstrifeapi.com/api/NationBuildings?APICode=f1240165d97856f&NationId={nation_id}'  # Replace with actual API URL
    response = requests.get(url)
    return response.json()

# Calculate military base stats
def calculate_military_bases(total_slots, army_bases, air_bases, naval_bases):
    army_percentage = (army_bases / (total_slots * 0.08)) * 100
    air_percentage = (air_bases / (total_slots * 0.04)) * 100
    naval_percentage = (naval_bases / (total_slots * 0.04)) * 100
    
    return (
        f"Army Bases: {army_bases}/{math.ceil(total_slots * 0.08)} ({round(army_percentage)}%)\n"
        f"Air Bases: {air_bases}/{math.ceil(total_slots * 0.04)} ({round(air_percentage)}%)\n"
        f"Naval Bases: {naval_bases}/{math.ceil(total_slots * 0.04)} ({round(naval_percentage)}%)"
    )

# Format the data into a readable format
def format_buildings(data):
    nation_data = data[0]  # Assuming the response is a list with the nation data

    # Extract relevant data
    power_buildings = f"{nation_data['TraditionalPowerPlants']} Power Plants, {nation_data['NuclearPlants']} Nuclear, {nation_data['SolarPlants']} Solar, {nation_data['WindPlants']} Wind"
    districts = f"{nation_data['CommercialDistricts']} Commercial Districts, {nation_data['FactoryDistricts']} Factory Districts, {nation_data['FuelExtractors']} Fuel Extractors, {nation_data['MiningDistricts']} Mining Districts, {nation_data['EntertainmentDistricts']} Entertainment Districts, {nation_data['ResidentialDistricts']} Residential Districts"
    schools_universities = f"{nation_data['SchoolDistricts']} School Districts, {nation_data['Universitys']} Universities, {nation_data['TradeSchools']} Trade Schools, {nation_data['ResearchCenters']} Research Centers"
    transportation = f"{nation_data['Roads']} Roads, {nation_data['RailNetworks']} Rail Networks, {nation_data['Ports']} Ports, {nation_data['Airports']} Airports, {nation_data['Subways']} Subways"
    
    # Calculate military base stats
    military_bases = calculate_military_bases(nation_data['TotalSlots'], nation_data['ArmyBases'], nation_data['AirBases'], nation_data['NavalBases'])
    
    # Total slots and open slots
    slots_info = f"Total Slots: {nation_data['TotalSlots']}, Open Slots: {nation_data['OpenSlots']}"

    # Combine everything into a formatted message
    result = (
        f"**Nation Buildings Info**\n\n"
        f"**Power Buildings**\n{power_buildings}\n\n"
        f"**Districts**\n{districts}\n\n"
        f"**Schools & Universities**\n{schools_universities}\n\n"
        f"**Transportation**\n{transportation}\n\n"
        f"**Military Bases**\n{military_bases}\n\n"
        f"**Slots Info**\n{slots_info}"
    )
    return result

@bot.command()
async def buildings(ctx, member: discord.Member):
    # Load user data and check if the user exists
    user_data = load_data(DATA_FILE)
    user_id = str(member.id)
    
    if user_id not in user_data:
        await ctx.send(f"Could not find nation ID for {member.mention}.")
        return

    # Get nation ID from USER_DATA.json
    nation_id = user_data[user_id]

    # Fetch nation data from the API
    nation_data = fetch_nation_data(nation_id)

    # Format and send the buildings info
    formatted_data = format_buildings(nation_data)
    await ctx.send(formatted_data)


def fetch_funds_data(nation_id):
    url = f"https://diplomacyandstrifeapi.com/api/AllianceMemberFunds?APICode=f1240165d97856f"
    response = requests.get(url)
    
    # Check if the response is successful
    if response.status_code == 200:
        data = response.json()
        for nation in data:
            if nation["NationId"] == nation_id:
                return nation
    return None  # Return None if the nation is not found

# Format large numbers with K, M, B
def format_number(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)

# Format the funds data
def format_funds_data(funds_data):
    return (
        f"**Nation Funds Information**\n"
        f"Cash: {format_number(funds_data['Cash'])}\n"
        f"Tech: {format_number(funds_data['Tech'])}\n"
        f"Production: {format_number(funds_data['Production'])}\n"
        f"Minerals: {format_number(funds_data['Minerals'])}\n"
        f"Uranium: {format_number(funds_data['Uranium'])}\n"
        f"Rare Metals: {format_number(funds_data['RareMetals'])}\n"
        f"Fuel: {format_number(funds_data['Fuel'])}\n"
        f"Political Power: {format_number(funds_data['PoliticalPower'])}"
    )


@bot.command()
async def funds(ctx, member: discord.Member):
    # Load user data and get the nation ID
    user_data = load_data(DATA_FILE)
    user_id = str(member.id)

    if user_id not in user_data:
        await ctx.send(f"Could not find nation ID for {member.mention}.")
        return

    # Get nation ID from USER_DATA.json
    nation_id = user_data[user_id]

    # Fetch the funds data from the API
    funds_data = fetch_funds_data(nation_id)

    if not funds_data:
        await ctx.send(f"Could not retrieve funds data for nation ID: {nation_id}.")
        return

    # Format and send the data
    formatted_data = format_funds_data(funds_data)
    await ctx.send(formatted_data)


@bot.command(name="warinfo")
async def warinfo(ctx, member: discord.Member):
    # Get nation ID for the mentioned user
    user_data = load_data(DATA_FILE)
    discord_id = str(member.id)
    nation_id = user_data.get(discord_id)
    
    if not nation_id:
        await ctx.send(f"User {member.mention} does not have a registered Nation ID.")
        return
    
    # Fetch data from API
    url = f"https://diplomacyandstrifeapi.com/api/NationWarHistory?APICode=f1240165d97856f&NationId={nation_id}&OnlyActive=true"
    response = requests.get(url)
    
    if response.status_code != 200:
        await ctx.send("Failed to retrieve data from the API.")
        return
    
    wars = response.json()
    
    # Sort wars into offensive and defensive
    offensive_wars = [war for war in wars if war["DeclareingNationId"] == nation_id]
    defensive_wars = [war for war in wars if war["DefendingNationId"] == nation_id]
    
    # Generate response message
    nation_url = f"https://diplomacyandstrife.com/nation/{nation_id}"
    msg = ""
    
    # Offensive Wars
    msg += f"\n**Offensive Wars ({len(offensive_wars)}/5):**\n"
    if offensive_wars:
        for i, war in enumerate(offensive_wars, start=1):
            defender_url = f"https://diplomacyandstrife.com/nation/{war['DefendingNationId']}"
            msg += (
                f"{i}. {war['DefendingNationName']}(<{defender_url}>)\n"
                f"   - Alliance: {war['DefendingNationAlliance']}\n"
                f"   - Offender Victory Points: {war['DeclareingNationVictoryPoints']}\n"
                f"   - Defender Victory Points: {war['DefendingNationVictoryPoints']}\n"
            )
    else:
        msg += "None\n"
    
    # Defensive Wars
    msg += f"\n**Defensive Wars ({len(defensive_wars)}/2):**\n"
    if defensive_wars:
        for i, war in enumerate(defensive_wars, start=1):
            attacker_url = f"https://diplomacyandstrife.com/nation/{war['DeclareingNationId']}"
            msg += (
                f"{i}. {war['DeclareingNationName']}(<{attacker_url}>)\n"
                f"   - Alliance: {war['DeclareingNationAlliance']}\n"
                f"   - Offender Victory Points: {war['DeclareingNationVictoryPoints']}\n"
                f"   - Defender Victory Points: {war['DefendingNationVictoryPoints']}\n"
            )
    else:
        msg += "None\n"
    
    response = await ctx.send(msg)




API_URLQUAL = "https://diplomacyandstrifeapi.com/api/AllianceTech?APICode=458d6abf27cba33"

@bot.command()
async def quality(ctx, member: discord.Member):
    USER_DATA = load_data(DATA_FILE)
    user_id = str(member.id)
    if user_id not in USER_DATA:
        await ctx.send(f"User {member.mention} not found in USER_DATA.json.")
        return

    nation_id = USER_DATA[user_id]

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URLQUAL) as response:
            if response.status != 200:
                await ctx.send("Failed to fetch data from the API.")
                return
            api_data = await response.json()

    # Find nation data
    nation_data = next((item for item in api_data if item["nationID"] == nation_id), None)
    if not nation_data:
        await ctx.send(f"No data found for nation ID {nation_id}.")
        return

    # Calculate qualities
    infantry_quality = nation_data["InfantryEquipment"]
    support_vehicles_quality = infantry_quality
    artillery_quality = nation_data["OrdnanceDevolopment"]
    light_tanks_quality = math.floor((infantry_quality / 2) + (nation_data["TankTechnology"] / 2))
    light_mechs_quality = math.floor((infantry_quality / 2) + (nation_data["MechDevolopment"] / 2))
    heavy_mechs_quality = math.floor((nation_data["ArmourImprovment"] / 2) + (nation_data["MechDevolopment"] / 2))
    precursor_mechs_quality = math.floor(nation_data["ArmourImprovment"] / 4 + (nation_data["MechDevolopment"]/4 + nation_data["PrecursorTech"]/2))
    missile_launchers_quality = nation_data["Rocketry"]
    fighters_quality = nation_data["AerospaceDevelopment"]
    helicopters_quality = nation_data["AerospaceDevelopment"]
    drones_quality = nation_data["ElectronicWarfare"]
    stealth_fighters_quality = math.floor((nation_data["StealthTechnology"] / 2) + (nation_data["AerospaceDevelopment"] / 2))
    destroyers_quality = math.floor((nation_data["SensorTechnology"] / 2) + (nation_data["NavalTechnology"] / 2))
    subs_quality = math.floor((nation_data["StealthTechnology"] / 2) + (nation_data["NavalTechnology"] / 2))
    cruisers_quality = math.floor((nation_data["NavalTechnology"] / 2) + (nation_data["Rocketry"] / 2))
    battleships_quality = math.floor((nation_data["OrdnanceDevolopment"] / 2) + (nation_data["NavalTechnology"] / 2))

    # Prepare and send response
    response = (
        f"**Quality Data for {nation_data['NationName']}**\n"
        f"- Infantry: {infantry_quality}\n"
        f"- Support Vehicles: {support_vehicles_quality}\n"
        f"- Artillery: {artillery_quality}\n"
        f"- Light Tanks: {light_tanks_quality}\n"
        f"- Light Mechs: {light_mechs_quality}\n"
        f"- Heavy Mechs: {heavy_mechs_quality}\n"
        f"- Precursor Mechs: {precursor_mechs_quality}\n"
        f"- Missile Launchers: {missile_launchers_quality}\n"
        f"- Fighters: {fighters_quality}\n"
        f"- Helicopters: {helicopters_quality}\n"
        f"- Drones: {drones_quality}\n"
        f"- Stealth Fighters: {stealth_fighters_quality}\n"
        f"- Destroyers: {destroyers_quality}\n"
        f"- Submarines: {subs_quality}\n"
        f"- Cruisers: {cruisers_quality}\n"
        f"- Battleships: {battleships_quality}\n"
        f"**DATA COULD BE +/-2 TO THE ACTUAL QUALITY**\n"
    )
    await ctx.send(response)


@bot.command()
async def military(ctx, member: discord.Member):
    # Check if the user has permission to view this stockpile
    user_id = str(member.id)  # Convert Discord user ID to a string
    USER_DATA = load_data(DATA_FILE)
    if user_id not in USER_DATA:
        await ctx.send(f"REGISTER!!! smh")
        return

    if not has_permission(ctx, user_id):
     await ctx.send("You do not have permission to check this user's stockpile.")
     return
    try:
        nation_id = int(USER_DATA[user_id])  # Fetch and convert the nation ID
    except ValueError:
        await ctx.send(f"Invalid nation ID for {member.mention} in USER_DATA.json.")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get("https://diplomacyandstrifeapi.com/api/AllianceMilitary?APICode=f1240165d97856f") as response:
            if response.status != 200:
                await ctx.send("Failed to fetch data from the API.")
                return
            api_data = await response.json()

    # Find nation data
    military_data = next((item for item in api_data if item["NationId"] == nation_id), None)
    if not military_data:
        await ctx.send(f"No data found for nation ID {nation_id}.")
        return

    # Fetch military data
    infantry = military_data["Infantry"]
    support_vehicles = military_data["SupportVehicles"]
    light_tanks = military_data["LightTanks"]
    medium_tanks = military_data["MediumTanks"]
    heavy_tanks = military_data["HeavyTanks"]
    light_mechs = military_data["LightMechs"]
    heavy_mechs = military_data["HeavyMechs"]
    precursor_mechs = military_data["PrescusarMech"]
    artillery = military_data["Artillery"]
    missile_launchers = military_data["MissileLaunchers"]
    fighters = military_data["Fighters"]
    bombers = military_data["Bombers"]
    helicopters = military_data["Helicopters"]
    drones = military_data["Drones"]
    stealth_fighters = military_data["StealthFighters"]
    stealth_bombers = military_data["StealthBombers"]
    destroyers = military_data["Destroyers"]
    subs = military_data["Subs"]
    carriers = military_data["Carriers"]
    cruisers = military_data["Cruisers"]
    battleships = military_data["Battleships"]

    infantry_cap = military_data["InfantryCapacity"]
    artillery_cap = military_data["ArtilleryCapacity"]
    armor_cap = military_data["ArmourCapacity"]
    air_cap = military_data["AirCapacity"]
    naval_cap = military_data["NavalCapacity"]

    # Constructing the response
    response = (
        f"**Military Data for {military_data['NationName']}**\n"
        f"Infantry: {infantry}, ({(infantry / infantry_cap * 100):.0f}%), Q{military_data['InfantryQuality']:.0f}\n"
        f"Support Vehicles: {support_vehicles}, ({(support_vehicles * 100 / infantry_cap *100):.0f}%), Q{military_data['SupportVehiclesQuality']:.0f}\n"
        f"Light Tanks: {light_tanks}, ({(light_tanks / armor_cap * 100):.0f}%), Q{military_data['LightTanksQuality']:.0f}\n"
        f"Medium Tanks: {medium_tanks}, ({(medium_tanks * 2 / armor_cap * 100):.0f}%), Q{military_data['MediumTanksQuality']:.0f}\n"
        f"Heavy Tanks: {heavy_tanks}, ({(heavy_tanks * 3.3 / armor_cap * 100):.0f}%), Q{military_data['HeavyTanksQuality']:.0f}\n"
        f"Light Mechs: {light_mechs}, ({(light_mechs * 1.3 / armor_cap * 100):.0f}%), Q{military_data['LightMechsQuality']:.0f}\n"
        f"Heavy Mechs: {heavy_mechs}, ({(heavy_mechs * 4 / armor_cap * 100):.0f}%), Q{military_data['HeavyMechsQuality']:.0f}\n"
        f"Precursor Mechs: {precursor_mechs}, ({(precursor_mechs * 10 / armor_cap * 100):.0f}%), Q{military_data['PrescusarMechQuality']:.0f}\n"
        f"Artillery: {artillery}, ({(artillery / artillery_cap * 100):.0f}%), Q{military_data['ArtilleryQuality']:.0f}\n"
        f"Missile Launchers: {missile_launchers}, ({(missile_launchers * 4 / artillery_cap * 100):.0f}%), Q{military_data['MissileLaunchersQuality']:.0f}\n"
        f"Fighters: {fighters}, ({(fighters / air_cap * 100):.0f}%), Q{military_data['FightersQuality']:.0f}\n"
        f"Bombers: {bombers}, ({(bombers / air_cap * 100):.0f}%), Q{military_data['BombersQuality']:.0f}\n"
        f"Helicopters: {helicopters}, ({(helicopters / air_cap * 100):.0f}%), Q{military_data['HelicoptersQuality']:.0f}\n"
        f"Drones: {drones}, ({(drones * 0.5 / air_cap * 100):.0f}%), Q{military_data['DronesQuality']:.0f}\n"
        f"Stealth Fighters: {stealth_fighters}, ({(stealth_fighters * 3 / air_cap * 100):.0f}%), Q{military_data['StealthFightersQuality']:.0f}\n"
        f"Stealth Bombers: {stealth_bombers}, ({(stealth_bombers * 3 / air_cap * 100):.0f}%), Q{military_data['StealthBombersQuality']:.0f}\n"
        f"Destroyers: {destroyers}, ({(destroyers * 0.6 / naval_cap * 100):.0f}%), Q{military_data['DestroyersQuality']:.0f}\n"
        f"Submarines: {subs}, ({(subs / naval_cap * 100):.0f}%), Q{military_data['SubsQuality']:.0f}\n"
        f"Carriers: {carriers}, ({(carriers * 10 / naval_cap * 100):.0f}%), Q{military_data['CarriersQuality']:.0f}\n"
        f"Cruisers: {cruisers}, ({(cruisers * 1.5 / naval_cap * 100):.0f}%), Q{military_data['CruisersQuality']:.0f}\n"
        f"Battleships: {battleships}, ({(battleships * 6 / naval_cap * 100):.0f}%), Q{military_data['BattleshipsQuality']:.0f}\n"
    )

    await ctx.send(response)




def get_nation_id_from_user(user_id):
    data = load_data(DATA_FILE)
    return data.get(str(user_id), None)
@bot.command()
async def track(ctx, user: discord.User, enemy_nation_id: int):
    user_nation_id = get_nation_id_from_user(user.id)
    if not user_nation_id:
        await ctx.send(f"Could not find nation for user {user.name}.")
        return

    # Fetch the user's war history
    war_history_url = f"https://diplomacyandstrifeapi.com/api/NationWarHistory?APICode=f1240165d97856f&NationId={user_nation_id}&OnlyActive=true"
    war_history_response = requests.get(war_history_url)
    war_history = war_history_response.json()

    # Find the matching war ID
    war_id = None
    for war in war_history:
        if war['DefendingNationId'] == enemy_nation_id or war['DeclareingNationId'] == enemy_nation_id:
            war_id = war['WarId']
            war_details = war
            break

    if not war_id:
        await ctx.send(f"No active war found between your nation and the enemy nation.")
        return

    # Fetch the war actions for the found WarId
    war_actions_url = f"https://diplomacyandstrifeapi.com/api/WarActionHistory?APICode=f1240165d97856f&WarId={war_id}"
    war_actions_response = requests.get(war_actions_url)
    war_actions = war_actions_response.json()

    # Load tracking data
    tracking_data = load_data(TRACKING_FILE)

    # Check if war is already being tracked
    if str(war_id) in tracking_data:
        await ctx.send("This war is already being tracked.")
        return

    # Save new war actions in tracking.json
    tracking_data[str(war_id)] = {
        'channel_id': str(ctx.channel.id),
        'war_actions': [action['Message'] for action in war_actions]
    }
    save_data(TRACKING_FILE, tracking_data)

    # Prepare the embed for initial war details
    embed = discord.Embed(
        title="War Tracking Started",
        description=f"A new war has been found and is now being tracked!",
        color=discord.Color.red()
    )
    embed.add_field(name="War ID", value=war_id, inline=True)
    embed.add_field(name="Enemy Nation", value=f"ID: {enemy_nation_id}", inline=True)
    embed.add_field(name="Declareing Nation", value=war_details['DeclareingNationName'], inline=True)
    embed.add_field(name="Defending Nation", value=war_details['DefendingNationName'], inline=True)
    embed.add_field(name="War Type", value=war_details['WarType'], inline=True)
    embed.add_field(name="Reason", value=war_details['WarReason'], inline=True)
    embed.add_field(
        name="Links",
        value=f"[Enemy Nation](https://diplomacyandstrife.com/home/{war_details['DeclareingNationId']}) | "
              f"[Defending Nation](https://diplomacyandstrife.com/home/{war_details['DefendingNationId']})",
        inline=False
    )
    embed.set_footer(text="Tracking war actions... Updates will be sent here.")

    await ctx.send(embed=embed)

    # Send initial war actions in the channel
    for action in war_actions:
        action_embed = discord.Embed(
            title="War Action",
            description=action['Message'],
            color=discord.Color.blue()
        )
        action_embed.set_footer(text=f"Timestamp: {action['TimeStampTxt']}")
        await ctx.send(embed=action_embed)

    await ctx.send(f"Tracking war actions for WarId: {war_id}")

@bot.command()
async def stop(ctx, war_id: int):
    # Load tracking data
    tracking_data = load_data(TRACKING_FILE)

    # Check if the provided WarId exists in tracking.json
    if str(war_id) not in tracking_data:
        await ctx.send(f"War ID {war_id} is not currently being tracked.")
        return

    # Remove the WarId entry from tracking.json
    del tracking_data[str(war_id)]
    save_data(TRACKING_FILE, tracking_data)

    # Notify the user
    await ctx.send(f"Stopped tracking war with ID: {war_id}.")

# Periodically check for new war actions and send them to the tracked channels
@tasks.loop(hours=1)
async def check_new_war_actions():
    tracking_data = load_data(TRACKING_FILE)
    
    for war_id, data in tracking_data.items():
        war_actions_url = f"https://diplomacyandstrifeapi.com/api/WarActionHistory?APICode=458d6abf27cba33&WarId={war_id}"
        war_actions_response = requests.get(war_actions_url)
        war_actions = war_actions_response.json()

        # Get already sent war actions
        sent_actions = set(data['war_actions'])
        new_actions = [action for action in war_actions if action['Message'] not in sent_actions]

        if new_actions:
            channel = bot.get_channel(int(data['channel_id']))
            if channel:
                for action in new_actions:
                    # Send embed for each new action
                    action_embed = discord.Embed(
                        title="New War Action",
                        description=action['Message'],
                        color=discord.Color.blue()  # Change color dynamically if needed
                    )
                    action_embed.set_footer(text=f"Timestamp: {action['TimeStampTxt']}")
                    await channel.send(embed=action_embed)

            # Update tracking data
            tracking_data[war_id]['war_actions'].extend([action['Message'] for action in new_actions])
            save_data(TRACKING_FILE, tracking_data)

@bot.command()
async def update_tracking(ctx, war_id: int):
    # Load tracking data
    tracking_data = load_data(TRACKING_FILE)

    # Check if the provided WarId exists in tracking.json
    if str(war_id) not in tracking_data:
        await ctx.send(f"War ID {war_id} is not currently being tracked.")
        return

    # Fetch the war actions for the specified WarId
    war_actions_url = f"https://diplomacyandstrifeapi.com/api/WarActionHistory?APICode=f1240165d97856f&WarId={war_id}"
    war_actions_response = requests.get(war_actions_url)
    war_actions = war_actions_response.json()

    # Get already sent war actions
    sent_actions = set(tracking_data[str(war_id)]['war_actions'])
    new_actions = [action for action in war_actions if action['Message'] not in sent_actions]

    if not new_actions:
        await ctx.send(f"No new actions found for War ID {war_id}.")
        return

    # Get the channel where updates are sent
    channel = bot.get_channel(int(tracking_data[str(war_id)]['channel_id']))
    if not channel:
        await ctx.send(f"Channel for War ID {war_id} not found.")
        return

    # Send new actions to the channel
    for action in new_actions:
        action_embed = discord.Embed(
            title="War Action",
            description=action['Message'],
            color=discord.Color.blue()  # Change this dynamically if needed
        )
        action_embed.set_footer(text=f"Timestamp: {action['TimeStampTxt']}")
        await channel.send(embed=action_embed)

    # Update tracking data
    tracking_data[str(war_id)]['war_actions'].extend([action['Message'] for action in new_actions])
    save_data(TRACKING_FILE, tracking_data)

    await ctx.send(f"Updated tracking for War ID {war_id} with {len(new_actions)} new actions.")


#WARS NOTIFICATION
API_URLOP = "https://diplomacyandstrifeapi.com/api/AllianceWarHistory?APICode=458d6abf27cba33&AllianceId=1332"
OFFENSIVE_CHANNEL_ID = 1312417937864396910  # Replace with your offensive war channel ID
DEFENSIVE_CHANNEL_ID = 1312418049550454845  # Replace with your defensive war channel ID
# Fetch API data
async def fetch_api_data():
    try:
        response = requests.get(API_URLOP)
        response.raise_for_status()  # Raise error for HTTP failures
        return response.json()
    except requests.RequestException as e:
        print(f"API REQUEST FAILED: {e}")
        return None

# Update war data
async def update_war_data(api_data):
    try:
        current_data = load_data(WAR_DATA_FILE)
        current_war_ids = set(current_data.keys())
        api_war_ids = set(str(war["WarId"]) for war in api_data)

        # Remove old wars not in API data
        for war_id in current_war_ids - api_war_ids:
            print(f"Removing WarId {war_id} from war_data.json")
            del current_data[war_id]

        # Add new wars and update existing
        for war in api_data:
            war_id = str(war["WarId"])
            current_data[war_id] = war

        save_data(WAR_DATA_FILE, current_data)
        print("war_data.json updated successfully.")
    except Exception as e:
        print(f"Error updating war data: {e}")

def get_user_id_from_nation(nation_id, nation_data):
    for user_id, nation in nation_data.items():
        if nation == nation_id:
            return user_id
    return None  # Return None if no match is found


# Notify wars
@tasks.loop(minutes=5)
async def notify_wars():
    try:
        war_data = load_data(WAR_DATA_FILE)
        notified_wars = load_data(NOTIFIED_FILE)
        nation_data = load_data(DATA_FILE)

        for war_id, war in war_data.items():
            if war_id in notified_wars:
                continue  # Skip already notified wars

            # Determine ally and enemy
            if war["DeclareingNationAllianceId"] == 1332:
                ally, enemy = war["DeclareingNationName"], war["DefendingNationName"]
                channel_id, ally_id, enemy_id = OFFENSIVE_CHANNEL_ID, war["DeclareingNationId"], war["DefendingNationId"]
                enemy_alliance = war["DefendingNationAlliance"]
                message_type = "offensive"
            elif war["DefendingNationAllianceId"] == 1332:
                ally, enemy = war["DefendingNationName"], war["DeclareingNationName"]
                channel_id, ally_id, enemy_id = DEFENSIVE_CHANNEL_ID, war["DefendingNationId"], war["DeclareingNationId"]
                enemy_alliance = war["DeclareingNationAlliance"]
                message_type = "defensive"
            else:
                continue  # Skip irrelevant wars
            user_id = get_user_id_from_nation(ally_id, nation_data)
            # Create embed message
            mention = f"<@{user_id}>"
            embed = discord.Embed(title="War Notification", color=discord.Color.red())
            embed.description = (
                f"**Ally**: [{ally}](https://diplomacyandstrife.com/nation/{ally_id})\n"
                f"**Enemy**: [{enemy}](https://diplomacyandstrife.com/nation/{enemy_id})\n"
                f"**EnemyAllianceName**: {enemy_alliance}\n"
                f"**War ID**: {war_id}\n"
                f"**War Type**: {war['WarType']}\n"
                f"**Reason**: {war['WarReason']}\n"
                f"**Mentioned User**: <@{user_id}>" 
            )

            # Send to appropriate channel
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(mention, embed=embed)
                notified_wars.append(war_id)
                print(f"Notified about War ID {war_id}")

        save_data(NOTIFIED_FILE, notified_wars)
    except Exception as e:
        print(f"Error in notify_wars: {e}")

# Periodic updates
@tasks.loop(minutes=5)
async def periodic_update():
    api_data = await fetch_api_data()
    if api_data:
        await update_war_data(api_data)

# Force notification command
@bot.command()
async def force_notify(ctx):
    await notify_wars()
    await ctx.send("War notifications processed!")

# On bot ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    notify_wars.start()
    periodic_update.start()

def load_war_data():
    with open(WAR_DATA_FILE, 'r') as f:
        return json.load(f)

# Define the !stat command
@bot.command(name="stat")
async def stat_command(ctx, war_id: int):
    war_data = load_war_data()
    

    
    # Check if WarId exists in the data
    if str(war_id) not in war_data:
        await ctx.send(f"Error: WarId {war_id} not found in war data.")
        return

# Function to format numbers
    def format_number(num):
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    # Get the war details for the given WarId
    war = war_data[str(war_id)]

    # Determine ally and enemy keys
    ally_key = "DeclareingNation" if war["DeclareingNationAllianceId"] == 1332 else "DefendingNation"
    enemy_key = "DefendingNation" if ally_key == "DeclareingNation" else "DeclareingNation"

    # Start building the response
    response = f"**War Information for WarId {war_id}:**\n"
    response += f"**Ally Nation**: {war[f'{ally_key}Name']} ({war[f'{ally_key}Id']}) | "
    response += f"**Enemy Nation**: {war[f'{enemy_key}Name']} ({war[f'{enemy_key}Id']})\n"
    response += f"**War Type**: {war['WarType']} | "
    response += f"**War Reason**: {war['WarReason']}\n"

    # Stolen Resources
    response += f"\n**Net Resources:**\n"
    response += f"**Cash Stolen**: {format_number(war[f'{ally_key}CashStolen'] - war[f'{enemy_key}CashStolen'])}\n"
    response += f"**Minerals Stolen**: {format_number(war[f'{ally_key}MineralStolen'] - war[f'{enemy_key}MineralStolen'])}\n"
    response += f"**Tech Stolen**: {format_number(war[f'{ally_key}TechStolen'] - war[f'{enemy_key}TechStolen'])}\n"
    response += f"**Uranium Stolen**: {format_number(war[f'{ally_key}UraniumStolen'] - war[f'{enemy_key}UraniumStolen'])}\n"
    response += f"**Rare Metals Stolen**: {format_number(war[f'{ally_key}RareMetalStolen'] - war[f'{enemy_key}RareMetalStolen'])}\n"
    response += f"**Fuel Stolen**: {format_number(war[f'{ally_key}FuelStolen'] - war[f'{enemy_key}FuelStolen'])}\n"

    # Lost Units
    response += f"\n**Net Units:**\n"
    response += f"**Infantry**: {format_number(war[f'{enemy_key}InfantryTotalLost'] - war[f'{ally_key}InfantryTotalLost'])}\n"
    response += f"**Support Vehicles**: {format_number(war[f'{enemy_key}SupportVehiclesTotalLost'] - war[f'{ally_key}SupportVehiclesTotalLost'])}\n"
    response += f"**Artillery**: {format_number(war[f'{enemy_key}ArtilleryTotalLost'] - war[f'{ally_key}ArtilleryTotalLost'])}\n"
    response += f"**Light Tanks**: {format_number(war[f'{enemy_key}LightTanksTotalLost'] - war[f'{ally_key}LightTanksTotalLost'])}\n"
    response += f"**Medium Tanks**: {format_number(war[f'{enemy_key}MediumTanksTotalLost'] - war[f'{ally_key}MediumTanksTotalLost'])}\n"
    response += f"**Heavy Tanks**: {format_number(war[f'{enemy_key}HeavyTanksTotalLost'] - war[f'{ally_key}HeavyTanksTotalLost'])}\n"
    response += f"**Light Mechs**: {format_number(war[f'{enemy_key}LightMechsTotalLost'] - war[f'{ally_key}LightMechsTotalLost'])}\n"
    response += f"**Heavy Mechs**: {format_number(war[f'{enemy_key}HeavyMechsTotalLost'] - war[f'{ally_key}HeavyMechsTotalLost'])}\n"
    response += f"**Prescusar Mechs**: {format_number(war[f'{enemy_key}PrescusarMechTotalLost'] - war[f'{ally_key}PrescusarMechTotalLost'])}\n"
    response += f"**Missile Launchers**: {format_number(war[f'{enemy_key}MissileLaunchersTotalLost'] - war[f'{ally_key}MissileLaunchersTotalLost'])}\n"
    response += f"**Bombers**: {format_number(war[f'{enemy_key}BombersTotalLost'] - war[f'{ally_key}BombersTotalLost'])}\n"
    response += f"**Fighters**: {format_number(war[f'{enemy_key}FightersTotalLost'] - war[f'{ally_key}FightersTotalLost'])}\n"
    response += f"**Helicopters**: {format_number(war[f'{enemy_key}HelicoptersTotalLost'] - war[f'{ally_key}HelicoptersTotalLost'])}\n"
    response += f"**Drones**: {format_number(war[f'{enemy_key}DronesTotalLost'] - war[f'{ally_key}DronesTotalLost'])}\n"
    response += f"**Stealth Fighters**: {format_number(war[f'{enemy_key}StealthFightersTotalLost'] - war[f'{ally_key}StealthFightersTotalLost'])}\n"
    response += f"**Stealth Bombers**: {format_number(war[f'{enemy_key}StealthBombersTotalLost'] - war[f'{ally_key}StealthBombersTotalLost'])}\n"
    response += f"**Destroyers**: {format_number(war[f'{enemy_key}DestroyersTotalLost'] - war[f'{ally_key}DestroyersTotalLost'])}\n"
    response += f"**Submarines**: {format_number(war[f'{enemy_key}SubsTotalLost'] - war[f'{ally_key}SubsTotalLost'])}\n"
    response += f"**Carriers**: {format_number(war[f'{enemy_key}CarriersTotalLost'] - war[f'{ally_key}CarriersTotalLost'])}\n"
    response += f"**Cruisers**: {format_number(war[f'{enemy_key}CruisersTotalLost'] - war[f'{ally_key}CruisersTotalLost'])}\n"
    response += f"**Battleships**: {format_number(war[f'{enemy_key}BattleshipsTotalLost'] - war[f'{ally_key}BattleshipsTotalLost'])}\n"

    # Send the response in the channel
    await ctx.send(response)
# Run the bot
if __name__ == "__main__":
   bot.run(os.getenv('DISCORD_BOT_TOKEN'))



