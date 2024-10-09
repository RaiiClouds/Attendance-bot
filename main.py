

import discord
from discord.ext import commands
from discord import app_commands
import os
import time
import sqlite3
import datetime
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN: str = os.getenv("TOKEN")
ID: int = os.getenv("ID") # server id
CHAN = 1292291459239776337 # admin only chan


class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        try:
            guild = discord.Object(id=ID)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')


intents = discord.Intents.default()
intents.message_content = True

# dont wory
client = Client(command_prefix="!", intents=intents)

# discord server id
GUILD_ID = discord.Object(id=ID)

database = sqlite3.connect('List.db')
cursor = database.cursor()
database.execute("CREATE TABLE IF NOT EXISTS team(Name STRING, Total INT, ClockIn INT, App STRING, Request INT, Role STRING)")


def checkClockedIn(user):
    cursor.execute(f"SELECT Name, App FROM team WHERE Name = ('{user}')")
    for row in cursor.fetchall():
        if "TRUE" in str(row):
            return True
        else:
            return False

class MyView(discord.ui.View):  # Create a class called MyView that subclasses discord.ui.View

    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def button_approved(self, interaction, button):
        button.disabled = True  # set button.disabled to True to disable the button
        button.label = (f"Approved by {interaction.user.name}")  # change the button's label to something else
        await interaction.response.edit_message(view=self)  # edit the message's view
        self.value = True
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def button_denied(self, interaction, button):
        button.disabled = True  # set button.disabled to True to disable the button
        button.label = (f"Denied by {interaction.user.name}")  # change the button's label to something else
        await interaction.response.edit_message(view=self)  # edit the message's view
        self.value = False
        self.stop()


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)

def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


@client.tree.command(name="list", description="List all users", guild=GUILD_ID)
async def button(interaction: discord.Interaction, team: int):
    if team == 1:
        ans = "SOFTWARE"
    elif team ==2:
        ans = "B&O"
    elif team ==3:
        ans = "MECHANICAL"
    else:
        ans = "IDK"
    

    embeds = []
    cursor.execute("SELECT * FROM team ORDER BY Total")
    cursor.execute(f"Select Name, Total, App FROM team WHERE Role = ('{ans}')")
    people = list(cursor.fetchall())
    chunks = list(divide_chunks(people, 25))
    for chunk in chunks:
        embed = discord.Embed(title="List of Users", description=f"Here is the list of all members from {ans}!", color=discord.Color.random(), timestamp=datetime.datetime.now())
        for row in chunk:
            embed.add_field(name=row[0], value=f"Total Time (HH:MM:SS): {convert(row[1])}\nCurrently Clocked In: {'No' if row[2] == 'FALSE' else 'Yes'}", inline=False)
        embeds.append(embed)

    await interaction.response.send_message(embeds=embeds)


@client.tree.command(name="clockin", description="Clock in (start your timer)", guild=GUILD_ID)
async def clockIn(interaction: discord.Interaction):
    app = False

    try:
        for row in cursor.execute(f"SELECT Name, App FROM team WHERE Name = ('{interaction.user.name}') "):
            if row != None:
                app = True
                if "TRUE" in str(row):
                    await interaction.response.send_message(f"You already clocked in {interaction.user.name}")
                else:
                    cursor.execute(
                        f"UPDATE team SET App = 'TRUE', ClockIN = {int(time.time())} WHERE Name = ('{interaction.user.name}')")
                    database.commit()

                    await interaction.response.send_message(f"Clocked in {interaction.user.name}")
    except Exception as e:
        print(f'Error syncing commands: {e}')

    if app == False:
        query = "INSERT INTO team VALUES(?, ?, ?, ?, ?, ?)"
        
        if discord.utils.get(interaction.guild.roles, name="software") in interaction.user.roles:
            cursor.execute(query, (interaction.user.name, 0, int(time.time()), "TRUE",0,"SOFTWARE"))
            
        elif discord.utils.get(interaction.guild.roles, name="business & outreach") in interaction.user.roles:
            cursor.execute(query, (interaction.user.name, 0, int(time.time()), "TRUE",0,"B&O"))
            
        elif discord.utils.get(interaction.guild.roles, name="mechanical") in interaction.user.roles:
            cursor.execute(query, (interaction.user.name, 0, int(time.time()), "TRUE",0,"MECHANICAL"))
            
        else:
            cursor.execute(query, (interaction.user.name, 0, int(time.time()), "TRUE",0,"IDK"))
        
        
        database.commit()

        await interaction.response.send_message(f"Clocked in {interaction.user.name}")




@client.tree.command(name="clockout", description="Clock out (stop your timer)", guild=GUILD_ID)  # Create a slash command
async def button(interaction: discord.Interaction):
    if not checkClockedIn(interaction.user.name):
        await interaction.response.send_message(f"You are not clocked in {interaction.user.name}")
        return
    if cursor.execute(f"SELECT App FROM team WHERE Name = ('{interaction.user.name}') ")== "FALSE":
        await interaction.response.send_message(f"You already requested to clock out{interaction.user.name}")
        return
        
    Channel = client.get_channel(CHAN)
    print(int(time.time()))
    cursor.execute(f"UPDATE team SET Request = {int(time.time())}, App = FALSE WHERE Name = ('{interaction.user.name}')")
    view = MyView()
    await interaction.response.send_message(f"Your request for clocking out has been sent.")
    await Channel.send(
        f"**{interaction.user.name}** has sent in a request to clock out, do you want to approve or deny time?",
        view=view)
    await view.wait()

    if view.value is None:
        return
    elif view.value == True:
        cursor.execute(f"Select Total, ClockIn, Request FROM team WHERE Name = ('{interaction.user.name}')")

        for row in cursor.fetchall():
            oldTime = row[0]
            clockInTime = row[1]
            request = row[2]

        newTime = request - clockInTime + oldTime

        cursor.execute(f"UPDATE team SET App = 'FALSE', Total = {newTime} WHERE Name = ('{interaction.user.name}')")
        database.commit()

        await interaction.channel.send(f"Thank you {interaction.user.name}, you worked for {convert(int(request - clockInTime))}")
    else:
        cursor.execute(f"UPDATE team SET App = 'FALSE' WHERE Name = ('{interaction.user.name}')")
        database.commit()
        await interaction.channel.send(f"{interaction.user.name} your request was not approved")






@client.tree.command(name="leave", description="Used To Leave If Clocked In By Accident", guild=GUILD_ID)
async def clockIn(interaction: discord.Interaction):
    cursor.execute(f"UPDATE team SET App = 'FALSE' WHERE Name = ('{interaction.user.name}')")
    database.commit()
    await interaction.response.send_message(f"Great you left {interaction.user.name}")




   
@client.tree.command(name="forceclockout", description="Used To force Everyone To Clockout But No Time Will Be awarded", guild=GUILD_ID)
async def clockIn(interaction: discord.Interaction):
    cursor.execute(f"UPDATE team SET App = 'FALSE'")
    database.commit()
    await interaction.response.send_message(f"Great you clocked out everyone")

client.run(TOKEN)