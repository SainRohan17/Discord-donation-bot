import discord
from discord import app_commands
import json
import os
from typing import Dict
from dotenv import load_dotenv
from datetime import datetime
from keep_alive import keep_alive

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

donations: Dict[str, list] = {}

DATA_FILE = "donations.json"

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

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    load_donations()
    
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print("Commands synced!")

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
        timestamp=datetime.now(datetime.UTC)
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
            timestamp=datetime.now(datetime.UTC)
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
            timestamp=datetime.now(datetime.UTC)
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
            timestamp=datetime.now(datetime.UTC)
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
        timestamp=datetime.now(datetime.UTC)
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

@donation_log.error
@user_donation.error
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
