import json
import pickle
from bs4 import BeautifulSoup as bs
from requests import Session
import os

class Subject( ):
    def __init__( self, name: str = None ) -> None:
        self.name: str = name
        self.total_grade: float = 0
        self.grades: dict[str, str] = { }
        self.absence: int = 0
        
    def __str__( self ):
        text = "" 
        
        for grade in self.grades:
            text += f"{grade[ 0 ]}: {grade[ 1 ]}\n"
            
        text += str( self.absence )
        
        return text

class Suap( ):
    def __init__( self ) -> None:
        self.session: Session = Session( )
        self.headers: dict[str, str] = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://suap.ifsuldeminas.edu.br/accounts/login/'
        }
        
        self.creds: dict[str, str] = self.load_creds( )
        self.soup: bs = self.login( )
        
        self.current_period: str = self.load_period( )
    
    def get_soup_instance( self, url, headers= None ) -> bs:
        page = self.session.get( url= url, headers= headers )
        return bs( page.text, 'html.parser' )
    
    def load_creds( self ) -> dict:
        creds = None
        
        try:
            with open( "configs/suap_creds.json", "r" ) as file:
                creds = json.load(file)
        except: 
            print( "[!] Erro em carregar notas.json" )
            exit( )
        
        return creds
        
    def login( self ) -> bs:
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

    def load_period( self ) -> str:
        period_selector: bs = self.soup.find( "select", { "id": "ano_periodo" } )
        return period_selector.find_next( "option" ).get_text( ).replace( "/", "-" )
        
    def get_subjects( self ) -> list[Subject]:
        if self.soup.find( "p", { "class" : "msg alert" } ):
            return []
        
        subject_rows_tag: list[bs] = self.soup.find( "table" ).find( "tbody" ).find_all( 'tr' )
        
        subjects_list = []
        
        for tag in subject_rows_tag:
            column_tag: list[bs] = tag.find_all( "td" )
            
            subject = Subject( )
            subject.name = column_tag[ 1 ].get_text( ).split( "-" )[1]
            subject.absence = int( column_tag[4].get_text( ) ) if not "-" in column_tag[4].get_text( ) else 0
            subject.total_grade = float( column_tag[11].get_text( ) ) if not "-" in column_tag[11].get_text( ) else 0
            
            popup_tag = column_tag[ 12 ].find_next( "a" )
            soup = self.get_soup_instance( f"https://suap.ifsuldeminas.edu.br{ popup_tag[ 'href' ] }?_popup=1", self.headers )
                        
            grade_tags: list[bs] = soup.find( "table" ).find( "tbody" ).find_all( 'tr' )
            for tag in grade_tags:
                column_tags: list[bs] = tag.find_all( 'td' )[ 0 : 6 ]
                sigla, _, descricao, _, valor, nota_obtida = [ tag.get_text() for tag in column_tags ]

                subject.grades[ ( descricao if descricao != '-' else sigla ) ] = f'{ nota_obtida } / { valor }'
                
            subjects_list.append( subject )
        
        return subjects_list
            
    def get_json_subjects( self ) -> dict:
        if not os.path.exists( 'periods' ):
            os.mkdir( 'periods' )
            
        try:
            with open( f"periods/{self.current_period}.json", "rb" ) as file:
                subjects = pickle.load(file)
                
                return subjects
            
        except FileNotFoundError:
            print( f"[!] Não existe {self.current_period}.json" )
            return None
                
        except IOError:
            print( f"[!] Erro em abrir {self.current_period}.json" )
            exit( )
            
        except Exception as e:
            print( f"[!] Exception: {e}" )
            exit( )

    def write_json_subjects( self, subjects: list[Subject] ):
        try:
            with open( f"periods/{self.current_period}.json", "wb" ) as file:
                pickle.dump( subjects, file, protocol= pickle.HIGHEST_PROTOCOL )
                
        except IOError:
            print( f"[!] Erro em abrir {self.current_period}.json" )
            exit( )
            
        except Exception as e:
            print( f"[!] Exception: {e}" )
            exit( )

    def get_subject( self, name: str ) -> Subject:
        for subject in self.get_subjects( ):
            if subject.name == name:
                return subject