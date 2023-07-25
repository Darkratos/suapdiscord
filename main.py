import discord
from discord import app_commands
from discord.ext import commands, tasks
from table2ascii import table2ascii as t2a, PresetStyle
from helpers.suap import Suap, Subject
from helpers.utils import get_discord_config
  
def main( ):
    token, channels_names, server_id = get_discord_config( )
    suap = Suap( )
    
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot( command_prefix= "1", intents= intents )

    @bot.tree.command( name="full", description= "Mostra todas notas e faltas" ) 
    async def full( interaction: discord.Interaction ):
        body = []
        
        for subject in suap.get_subjects( ):
            body.append( [subject.name, subject.absence, subject.total_grade] )
            
        output = t2a(
            header = [ "Matéria", "Faltas", "Nota" ],
            body = body,
            style= PresetStyle.thin_box
        )

        await interaction.response.send_message( content = f"```\n{ output }\n```" )

    @bot.tree.command( name= "detalhes", description= "Detalha uma matéria" ) 
    @app_commands.choices( choices= [ discord.app_commands.Choice( name= subject.name, value= subject.name ) for subject in suap.get_subjects( ) ] )
    async def detalhes( interaction: discord.Interaction, choices: app_commands.Choice[str] ):
        print(choices.name)

        subject = suap.get_subject( choices.name )
        body = []
        
        for name, grade in subject.grades:
            body.append( [ name, grade ] )
        
        output = t2a(
            header = [ "Atividade", "Nota" ],
            body = body,
            style= PresetStyle.thin_box
        )

        await interaction.response.send_message( content = f"```\n{ output }\n```" )

    @tasks.loop( minutes = 10 )
    async def check( ):
        updated_subjects = suap.get_subjects( )
        old_subjects = suap.get_json_subjects( )
        subjects_with_new_grades: list[Subject] = [ ]
        subjects_with_new_absence: list[Subject] = [ ]
        
        for old_subject, updated_subject in zip( old_subjects, updated_subjects ):
            old_subject: Subject
            updated_subject: Subject
            
            new_grades = [ updated_grade for old_grade, updated_grade in zip(old_subject.grades, updated_subject.grades) if updated_grade[1] != old_grade[1] ]            
            
            if len( new_grades ):
                subjects_with_new_grades.append( updated_subject )
                
            if old_subject.absence != updated_subject.absence:
                subjects_with_new_absence.append( updated_subject )
        
        if len( subjects_with_new_grades ):
            print( "[!] Novas notas" )
            suap.write_json_subjects( updated_subjects )
            
            for server in bot.guilds:
                channel = discord.utils.get( server.channels, name= channels_names[ "grades" ] )
                
                body = [ ]
                
                for subject in subjects_with_new_grades:
                    for name, grade in subject.grades:
                        body.append( [ name, grade ] )
                
                output = t2a(
                    header = [ "Atividade", "Nota" ],
                    body = body,
                    style= PresetStyle.thin_box
                )

                await channel.send( "<@Suap> ", embed= output )

        if len( subjects_with_new_absence ):
            print("[!] Novas faltas")
            suap.write_json_subjects( updated_subjects )
            
            for server in bot.guilds:
                channel = discord.utils.get( server.channels, name= channels_names[ "absences" ] )
                
                output = t2a(
                    header = [ "Matéria", "Faltas" ],
                    body = [ [ subject.name, subject.absence ] for subject in subjects_with_new_grades ],
                    style= PresetStyle.thin_box
                )

                await channel.send( "<@here> ", embed= output )

    @bot.event
    async def on_ready( ):
        await bot.tree.sync( guild=discord.Object( id= server_id) )

        check.start( )

    bot.run( token )
    
if __name__ == "__main__":
    main( )