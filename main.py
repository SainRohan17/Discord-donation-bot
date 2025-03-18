import discord
from discord import app_commands
import json
import os
import asyncio
from typing import Dict, List
from dotenv import load_dotenv
from datetime import datetime, timedelta
from keep_alive import keep_alive

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
TOKEN = os.getenv("TOKEN")

ROLE_NAMES = {
    "donor": "Donor",
    "orbital": "Orbital Donor",
    "galactic": "Galactic Donor",
    "cosmic": "Cosmic Donor"
}

ROLE_DURATIONS = {
    "orbital": 30,    
    "galactic": 90,   
    "cosmic": None    
}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

donations: Dict[str, list] = {}
role_expirations: Dict[str, Dict[str, datetime]] = {}

DATA_FILE = "donations.json"
ROLES_FILE = "role_expirations.json"

def load_donations():
    global donations
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            donations = json.load(f)
    else:
        donations = {}

def save_donations():
    with open(DATA_FILE, 'w') as f:
        json.dump(donations, f)

def load_role_expirations():
    global role_expirations
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE, 'r') as f:
            temp_data = json.load(f)
            role_expirations = {}
            for user_id, roles in temp_data.items():
                role_expirations[user_id] = {}
                for role, timestamp_str in roles.items():
                    if timestamp_str is not None:
                        role_expirations[user_id][role] = datetime.fromisoformat(timestamp_str)
                    else:
                        role_expirations[user_id][role] = None
    else:
        role_expirations = {}

def save_role_expirations():
    temp_data = {}
    for user_id, roles in role_expirations.items():
        temp_data[user_id] = {}
        for role, timestamp in roles.items():
            if timestamp is not None:
                temp_data[user_id][role] = timestamp.isoformat()
            else:
                temp_data[user_id][role] = None
    
    with open(ROLES_FILE, 'w') as f:
        json.dump(temp_data, f)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    load_donations()
    load_role_expirations()
    
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print("Commands synced!")
    
    client.loop.create_task(check_role_expirations())

async def check_role_expirations():
    await client.wait_until_ready()
    while not client.is_closed():
        print("Checking role expirations...")
        guild = client.get_guild(GUILD_ID)
        if not guild:
            print(f"Could not find guild with ID {GUILD_ID}")
            await asyncio.sleep(6 * 60 * 60)  
            continue
            
        current_time = datetime.utcnow()
        to_remove = []
        
        for user_id, roles in role_expirations.items():
            member = guild.get_member(int(user_id))
            if not member:
                print(f"Could not find member with ID {user_id}")
                continue
                
            for role_name, expiration_time in roles.items():
                if expiration_time is not None and current_time > expiration_time:
                    print(f"Role {role_name} expired for user {member.name} ({user_id})")
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role in member.roles:
                        try:
                            await member.remove_roles(role)
                            print(f"Removed {role_name} from {member.name}")
                            to_remove.append((user_id, role_name))
                        except discord.Forbidden:
                            print(f"Bot doesn't have permission to remove roles from {member.name}")
                        except Exception as e:
                            print(f"Error removing role: {e}")
        
        for user_id, role_name in to_remove:
            if user_id in role_expirations and role_name in role_expirations[user_id]:
                del role_expirations[user_id][role_name]
                if not role_expirations[user_id]:
                    del role_expirations[user_id]
        
        if to_remove:
            save_role_expirations()
            
        await asyncio.sleep(6 * 60 * 60)

@tree.command(
    name='donation_log',
    description='Record a donation from a user',
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.checks.has_permissions(administrator=True)
async def donation_log(interaction: discord.Interaction, user_id: str, amount: int):
    """Record a donation from a user"""
    if user_id in donations:
        donations[user_id].append(amount)
    else:
        donations[user_id] = [amount]
    
    save_donations()
    
    embed = discord.Embed(
        title="Donation Logged",
        description=f"A new donation has been recorded",
        color=0xF5CB7A,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="<:user:1351230258560503909>・User", value=f"<@{user_id}>", inline=False)
    embed.add_field(name="<:amount:1351230582343995432>・Amount", value=f"{amount}", inline=False)
    embed.add_field(name="<:donor:1351229804107661383>・Total Donations", value=f"{sum(donations[user_id])}", inline=False)
    embed.set_footer(text=f"Logged by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)

@tree.command(
    name='user_donation',
    description='Check donations made by a specific user',
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.checks.has_permissions(administrator=True)
async def user_donation(interaction: discord.Interaction, user_id: str):
    """Check donations made by a specific user"""
    if user_id in donations:
        total = sum(donations[user_id])
        
        embed = discord.Embed(
            title="Donation History",
            description=f"Donation history for <@{user_id}>",
            color=0xF5CB7A,
            timestamp=datetime.utcnow()
        )
        
        donation_list = donations[user_id]
        if len(donation_list) > 25:
            donation_list = donation_list[-25:]
            embed.add_field(name="Recent Donations", value="\n".join([f"• {amount}" for amount in donation_list]), inline=False)
            embed.add_field(name="Note", value="Only showing the 25 most recent donations", inline=False)
        else:
            embed.add_field(name="<:donor:1351229804107661383>・All Donations", value="\n".join([f"• {amount}" for amount in donation_list]), inline=False)
        
        embed.add_field(name="<:times:1351231037103149196>・Number of Donations", value=f"{len(donations[user_id])}", inline=False)
        embed.add_field(name="<:amount:1351230582343995432>・Total Amount", value=f"{total}", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.name}")
    
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="No Donations Found",
            description=f"No donations have been recorded for <@{user_id}>",
            color=0xF5CB7A,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

@tree.command(
    name='leaderboard',
    description='Display the top 10 donors by total donation amount',
    guild=discord.Object(id=GUILD_ID)
)
async def leaderboard(interaction: discord.Interaction):
    """Display the top 10 donors leaderboard"""
    if not donations:
        embed = discord.Embed(
            title="Donation Leaderboard",
            description="No donations have been recorded yet.",
            color=0xF5CB7A,
            timestamp=datetime.utcnow()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    totals = {user_id: sum(amounts) for user_id, amounts in donations.items()}
    
    sorted_donors = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    
    top_donors = sorted_donors[:10]
    
    embed = discord.Embed(
        title="<:top_donors:1351229089972752455>  Donation Leaderboard  <:top_donors:1351229089972752455>",
        description="Top donors by total donation amount",
        color=0xF5CB7A,
        timestamp=datetime.utcnow()
    )
    
    for i, (user_id, amount) in enumerate(top_donors, 1):
        prefix = ""
        if i == 1:
            prefix = "<:top_1:1351229655822368819>・"
        elif i == 2:
            prefix = "<:top_2:1351229634024439819>・"
        elif i == 3:
            prefix = "<:top_3:1351229621957562519>・"
        else:
            prefix = f"#{i} "
        
        embed.add_field(
            name=f"{prefix}Place",
            value=f"<@{user_id}>\nTotal: {amount}",
            inline=(i > 3) 
        )
    
    embed.set_footer(text=f"Requested by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)

@tree.command(
    name='give_role',
    description='Give donor role to a user',
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.checks.has_permissions(administrator=True)
async def give_role(
    interaction: discord.Interaction, 
    user_id: str, 
    role_type: str
):
    """Give donor role to a user"""
    if user_id not in donations:
        embed = discord.Embed(
            title="Role Assignment Failed",
            description=f"User <@{user_id}> has not made any donations yet.",
            color=0xF5CB7A,
            timestamp=datetime.utcnow()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    guild = interaction.guild
    
    try:
        member = await guild.fetch_member(int(user_id))
    except:
        embed = discord.Embed(
            title="Role Assignment Failed",
            description=f"Could not find user with ID: {user_id}",
            color=0xF5CB7A,
            timestamp=datetime.utcnow()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    if role_type not in ["orbital", "galactic", "cosmic"]:
        embed = discord.Embed(
            title="Role Assignment Failed",
            description="Invalid role type. Please choose from 'orbital', 'galactic', or 'cosmic'.",
            color=0xF5CB7A,
            timestamp=datetime.utcnow()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    role_name = role_type
    
    donor_role = discord.utils.get(guild.roles, name=ROLE_NAMES["donor"])
    tier_role = discord.utils.get(guild.roles, name=ROLE_NAMES[role_name])
    
    if not donor_role:
        donor_role = await guild.create_role(name=ROLE_NAMES["donor"], color=discord.Color.gold())
    
    if not tier_role:
        if role_name == "orbital":
            tier_role = await guild.create_role(name=ROLE_NAMES[role_name], color=discord.Color.blue())
        elif role_name == "galactic":
            tier_role = await guild.create_role(name=ROLE_NAMES[role_name], color=discord.Color.purple())
        elif role_name == "cosmic":
            tier_role = await guild.create_role(name=ROLE_NAMES[role_name], color=discord.Color.red())
    
    current_time = datetime.utcnow()
    expiration_time = None
    
    if ROLE_DURATIONS[role_name] is not None:
        expiration_time = current_time + timedelta(days=ROLE_DURATIONS[role_name])
    
    await member.add_roles(donor_role, tier_role)
    
    if user_id not in role_expirations:
        role_expirations[user_id] = {}
    
    role_expirations[user_id]["donor"] = expiration_time
    role_expirations[user_id][role_name] = expiration_time
    
    save_role_expirations()
    
    embed = discord.Embed(
        title="Role Assigned",
        description=f"Donor role has been assigned to <@{user_id}>",
        color=0xF5CB7A,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Role", value=f"{ROLE_NAMES[role_name]}", inline=True)
    
    if expiration_time:
        expiration_str = expiration_time.strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(name="Expires", value=expiration_str, inline=True)
    else:
        embed.add_field(name="Expires", value="Never (Permanent)", inline=True)
    
    embed.set_footer(text=f"Assigned by {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)

@give_role.autocomplete('role_type')
async def role_type_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    choices = [
        app_commands.Choice(name="Orbital Donor (1 month)", value="orbital"),
        app_commands.Choice(name="Galactic Donor (3 months)", value="galactic"),
        app_commands.Choice(name="Cosmic Donor (Permanent)", value="cosmic")
    ]
    return choices

@donation_log.error
@user_donation.error
@give_role.error
async def command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(
            title="Permission Error",
            description="You need administrator permissions to use this command.",
            color=0xF5CB7A
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(error)}",
            color=0xF5CB7A
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    keep_alive() 
    client.run(TOKEN)
