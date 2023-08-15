import json


def remove_unicode( str: str ) -> str:
        encoded_string = str.encode( 'ascii', 'ignore' )
        return encoded_string.decode( )  

def get_discord_config( ) -> tuple[str, str, int]:   
    try:
        with open( "configs/discord.json" ) as file:
            discord = json.load( file )
            token = discord[ "token" ]
            channel_names = discord[ "channelNames" ]
            server_id = discord[ "serverId" ]
            
            return token, channel_names, server_id
            
    except:
        print( "[!] Erro ao ler discord.json" )
        exit( )
      