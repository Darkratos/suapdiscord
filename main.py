import discord
from discord.ext import commands
from requests import Session
from bs4 import BeautifulSoup as bs
import json
import pickle
from table2ascii import table2ascii as t2a, PresetStyle


class Suap():
    def __init__(self) -> None:
        self.creds = None
        self.session = Session( )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://suap.ifsuldeminas.edu.br/accounts/login/'
        }
        
        self.load_creds( )
    
    def load_creds( self ):
        try:
            with open( "creds.json", "r" ) as file:
                self.creds = json.load( file )   
        except: 
            input( "[!] Erro em carregar notas.json" )
        
    def login( self ):
        parser = self.get_soup_instance( url= 'https://suap.ifsuldeminas.edu.br/accounts/login/', headers= self.headers )
        token = parser.find( 'input', { 'type': 'hidden' } )[ 'value' ]

        post_data = {
            'csrfmiddlewaretoken': token,
            'username': self.creds[ 'user' ],
            'password': self.creds[ 'pass' ],
            'this_is_the_login_form': '1',
            'next': '/',
            'g-recaptcha-response': ''
        }

        self.session.post( url= 'https://suap.ifsuldeminas.edu.br/accounts/login/', headers= self.headers, data= post_data )
        return self.get_soup_instance( url= f'https://suap.ifsuldeminas.edu.br/edu/aluno/{ self.creds[ "user" ] }/?tab=boletim', headers= self.headers )
        
    def get_soup_instance( self, url, headers= None ):
        page = self.session.get( url= url, headers= headers )
        return bs( page.text, 'html.parser' )


def remove_unicode( str ):
        encoded_string = str.encode( 'ascii', 'ignore' )
        return encoded_string.decode( )  

def main( ):
    suap = Suap( )
    bot = commands.Bot( command_prefix= "1", intents= discord.Intents.default( ) )

    @bot.tree.command( name="full", description= "Mostra todas notas e faltas", guild= discord.Object( id= 564238890316201987 ) ) 
    async def full( interaction: discord.Interaction ):
        soup = suap.login( )
        materia_rows = soup.select( ".borda > tbody:nth-child(2)" )[ 0 ].find_all( 'tr' )

        body = [ ]
        for tag in materia_rows:
            splits = tag.find_all( 'td' )
            materia = splits[ 1 ].text.split( ' - ' )[ 1 ]
            faltas = splits[ 8 ].text
            nota = splits[ 7 ].text
            
            body.append( [ materia, faltas, nota ] )

        output = t2a(
            header = [ "Matéria", "Faltas", "Nota" ],
            body = body,
            style= PresetStyle.thin_box
        )

        await interaction.response.send_message( content = f"```\n{ output }\n```" )

    @bot.event
    async def on_ready( ):
        await bot.tree.sync( guild= discord.Object( id= 564238890316201987 ) )
        
        soup = suap.login( )
        materia_popups_tags = soup.find_all( "a", { 'class': 'btn popup' } ) 

        dict_materias = { }
        for tag in materia_popups_tags:
            soup = suap.get_soup_instance( f"https://suap.ifsuldeminas.edu.br{ tag[ 'href' ] }?_popup=1", suap.headers )
            materia = remove_unicode( soup.select( '.title-container > h2:nth-child(1)' )[ 0 ].text[ 7 : ] )
            
            dict_materias[ materia ] = { }

            nota_tags = soup.select( 'html body.theme-luna.popup_ div.holder main#content div.box div table.borda tbody tr' )
            
            for tag in nota_tags:
                descricao, dummy, valor, nota_obtida = [ tag.text for tag in tag.find_all( 'td' )[ 2 : 6 ] ]

                if ( nota_obtida != '-' ):
                    dict_materias[ materia ][ descricao ] = f'{ nota_obtida } / { valor }'

        old_json = { }
        
        try:
            with open( "notas.json", "rb" ) as file:
                old_json = pickle.load( file )
                
        except FileNotFoundError:
            print( "[!] Criando notas.json" )
            with open( "notas.json", "wb" ) as file:
                pickle.dump( dict_materias, file, protocol= pickle.HIGHEST_PROTOCOL )
                
        except IOError:
            input( "[!] Erro em abrir notas.json" )
            
        except Exception as e:
            input( f"[!] Exception: {e}" )
            
        with open( "notas.json", "wb" ) as file:
            novo = { materia: dict_materias[ materia ] for materia in dict_materias.keys( ) if materia in old_json.keys( ) and dict_materias[ materia ] != old_json[ materia ] }
            pickle.dump( dict_materias, file, protocol= pickle.HIGHEST_PROTOCOL )
            
        if len( novo ):
            for server in bot.guilds:
                channel = discord.utils.get( server.channels, name = "📓suap" )

                text = ''
                for materia in novo:
                    title = materia
                    
                    text = "\n".join( [ f"{key}" for key in dict_materias[ materia ] ] )

                    embed = discord.Embed( title= title, description= text, color= discord.Color.blue( ), url= 'https://suap.ifsuldeminas.edu.br/accounts/login' )
                    await channel.send( "<@Suap> ", embed= embed )

    bot.run( suap.creds[ "token" ] )
    
if __name__ == "__main__":
    main( )