from genericpath import exists
import discord
from discord.ext import commands
from requests import Session
from bs4 import BeautifulSoup as bs
import json
import pickle

def remove_unicode( str ):
    encoded_string = str.encode( 'ascii', 'ignore' )
    return encoded_string.decode( )

client = discord.Client( intents= discord.Intents.default( ) )

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://suap.ifsuldeminas.edu.br/accounts/login/'
}

@client.event
async def on_ready( ):
    s = Session( )
    r = s.get( 'https://suap.ifsuldeminas.edu.br/accounts/login/', headers = headers )
    soup = bs( r.text, 'html.parser' )
    token = soup.find( 'input', { 'type': 'hidden' } )[ 'value' ]

    post_data = {
        'csrfmiddlewaretoken': token,
        'username': creds[ 'user' ],
        'password': creds[ 'pass' ],
        'this_is_the_login_form': '1',
        'next': '/',
        'g-recaptcha-response': ''
    }

    r = s.post( 'https://suap.ifsuldeminas.edu.br/accounts/login/', headers = headers, data = post_data )
    r = s.get( f'https://suap.ifsuldeminas.edu.br/edu/aluno/{ creds[ "user" ] }/?tab=boletim', headers = headers )

    soup = bs( r.text, 'html.parser' )

    materias = soup.find_all( "a", { 'class': 'btn popup' } ) 

    dict_materias = {}

    for m in materias:
        r = s.get( f"https://suap.ifsuldeminas.edu.br{ m[ 'href' ] }?_popup=1", headers = headers )
        soup = bs( r.text, 'html.parser' )
        materia = soup.select( '.title-container > h2:nth-child(1)' )[ 0 ].text[ 7 : ]
        materia = remove_unicode( materia )
        
        dict_materias[ materia ] = {}

        notas = soup.select( 'html body.theme-luna.popup_ div.holder main#content div.box div table.borda tbody tr' )
        
        for n in notas:
            tds = n.find_all( 'td' )

            if ( tds[ 5 ].text != '-' ):
                dict_materias[ materia ][ tds[ 2 ].text ] = f'{ tds[ 5 ].text } / { tds[ 4 ].text }'

    if not exists( "notas.json" ):
        with open( "notas.json", "wb" ) as f:
            pickle.dump( dict_materias, f, protocol= pickle.HIGHEST_PROTOCOL )

    with open( "notas.json", "rb" ) as f:
        old_json = pickle.load( f )

    with open( "notas.json", "wb" ) as f:
        novo = { k: dict_materias[ k ] for k in dict_materias if k in old_json and dict_materias[ k ] != old_json[ k ] }
        pickle.dump( dict_materias, f, protocol= pickle.HIGHEST_PROTOCOL )
        
    if len( novo ):
        for server in client.guilds:
            channel = discord.utils.get( server.channels, name = "notas" )

        for m in novo:
            title = m
            text = ''
        
            for k in dict_materias[ m ]:
                text += f"{ k }: { dict_materias[ m ][ k ] }\n"

            embed = discord.Embed( title = title, description = text, color = discord.Color.blue( ), url = 'https://suap.ifsuldeminas.edu.br/accounts/login' )
            await channel.send( embed = embed )

with open( "creds.json", "r" ) as f:
    creds = json.load( f )   

client.run( creds[ "token" ] )