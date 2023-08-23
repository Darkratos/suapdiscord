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
        await interaction.response.defer( ephemeral= True )

        body = []
        
        for subject in suap.get_subjects( ):
            body.append( [subject.name, subject.absence, subject.total_grade] )
            
        output = t2a(
            header = [ "Matéria", "Faltas", "Nota" ],
            body = body,
            style= PresetStyle.thin_box
        )

        await interaction.followup.send( content = f"```\n{ output }\n```", ephemeral= True )

    @bot.tree.command( name= "detalhes", description= "Detalha uma matéria" ) 
    @app_commands.choices( choices= [ discord.app_commands.Choice( name= subject.name, value= subject.name ) for subject in suap.get_subjects( ) ] )
    async def detalhes( interaction: discord.Interaction, choices: app_commands.Choice[str] ): 
        await interaction.response.defer( ephemeral= True  )

        subject = suap.get_subject( choices.name )
        body = []
        
        for name, grade in subject.grades.items( ):
            body.append( [ name, grade ] )
        
        output = t2a(
            header = [ "Atividade", "Nota" ],
            body = body,
            style= PresetStyle.thin_box
        )

        await interaction.followup.send( content = f"**{ choices.name }**\n```\n{ output }\n```", ephemeral= True )

    @tasks.loop( seconds= 1 )
    async def check( ):
        new_subjects = suap.get_subjects( )
        old_subjects = suap.get_json_subjects( )
        subjects_with_new_grades: list[Subject] = [ ]
        subjects_with_new_absence: list[Subject] = [ ]
        
        if old_subjects:
            for old_subject, new_subject in zip( old_subjects, new_subjects ):
                old_subject: Subject
                new_subject: Subject
                
                old_grade_values = old_subject.grades.values( )
                new_grade_values = new_subject.grades.values( )
                
                new_grades = [ new_grade for old_grade, new_grade in zip( old_grade_values, new_grade_values ) if new_grade != old_grade ]
                                
                if len( new_grades ):
                    subjects_with_new_grades.append( new_subject )
                    
                if old_subject.absence != new_subject.absence:
                    subjects_with_new_absence.append( new_subject )
        
        else:
            subjects_with_new_grades = new_subjects
            subjects_with_new_absence = new_subjects
            
        if len( subjects_with_new_grades ):
            print( "[!] Novas notas" )
            suap.write_json_subjects( new_subjects )
                        
            for server in bot.guilds:
                channel = discord.utils.get( server.channels, name= channels_names["grades"] )
                output = ""
                
                for subject in subjects_with_new_grades:
                    body = [ ]
                    
                    for name, grade in subject.grades.items( ):
                        body.append( [ name, grade ] )
                        
                    table = t2a(
                        header = [ "Atividade", "Nota" ],
                        body = body,
                        style= PresetStyle.thin_box
                    )
                
                    output += f"**{subject.name}**\n```{table}```\n\n"
                
                embed = discord.Embed( title= "Novas notas", description= output, url= f"https://suap.ifsuldeminas.edu.br/edu/aluno/{suap.creds['user']}/?tab=boletim" )

                await channel.send( "", embed= embed )

        if len( subjects_with_new_absence ):
            print("[!] Novas faltas")
            suap.write_json_subjects( new_subjects )
            
            for server in bot.guilds:
                channel = discord.utils.get( server.channels, name= channels_names["absences"] )
                
                output = t2a(
                    header = [ "Matéria", "Faltas" ],
                    body = [ [ subject.name, subject.absence ] for subject in subjects_with_new_absence ],
                    style= PresetStyle.thin_box
                )
                
                embed = discord.Embed( title= "Novas faltas", description= f"```\n{ output }\n```", url= f"https://suap.ifsuldeminas.edu.br/edu/aluno/{suap.creds['user']}/?tab=boletim" )

                await channel.send( "", embed= embed )

        check.change_interval( seconds= 0, minutes= 10 )

    @bot.event
    async def on_ready( ):
        await bot.tree.sync( )
        check.start( ) 

    bot.run( token )
    
if __name__ == "__main__":
    main( )