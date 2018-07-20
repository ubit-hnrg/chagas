# prerequisite https://github.com/brianb/mdbtools
import argparse
import sys, subprocess, os
import pandas as pd
import glob
import datetime


def get_args():
    parser = argparse.ArgumentParser(description=' full pipeline for dump and preprocess ChagasDB writed in Access')
    parser.add_argument('-i','--input_db',required=True)
    parser.add_argument('-o','--opath',required=True)  
    # parse args
    args = parser.parse_args()
    return args


# code addapted from AccessDump.py file
# A simple script to dump the contents of a Microsoft Access Database.
# It depends upon the mdbtools suite:
#   http://sourceforge.net/projects/mdbtools/
# Dump the schema for the DB
def DumpDb(imput_db,dump_path):
    subprocess.call(["mdb-schema", imput_db, "mysql"])

    # Get the list of table names with "mdb-tables"
    table_names = subprocess.Popen(["mdb-tables", "-1", imput_db],
                                stdout=subprocess.PIPE).communicate()[0]
    tables = table_names.splitlines()

    print "BEGIN;" # start a transaction, speeds things up when importing
    sys.stdout.flush() # te permite ver el print anterior inmediatamente en la consola

    # Dump each table as a CSV file using "mdb-export",
    # converting " " in table names to "_" for the CSV filenames.
    with open(dump_path + 'Chagas.sql','wb') as f:
        for table in tables:
            if table != '':
                #subprocess.call(["mdb-export", "-I", "mysql", imput_db, table])
                table_content = subprocess.Popen(["mdb-export", "-I", "mysql", imput_db, table],stdout=subprocess.PIPE).communicate()[0]                
            f.write(table_content)
    f.close()

    for table in tables:
        ffile = dump_path+table+'.csv'
        with open(ffile,'wb') as f:
            if table != '':
                tc = subprocess.Popen(['mdb-export', input_db, table],stdout=subprocess.PIPE).communicate()[0]
            f.write(tc)
        f.close()
    
    print "COMMIT;" # end the transaction
    sys.stdout.flush()


    #os.system('for x in `mdb-tables -1 %s`; do mdb-export %s $x >> %s.$x.csv ; done'%(input_db,input_db,dump_path))
    #os.system('mv %s.sqlite %s'%(input_db,dump_path))

def print_date(opath):
    now = datetime.datetime.now()
    nowstr = now.strftime("%Y-%m-%d %H:%M")
    with open(opath+'LastUpdate','wb') as f:
        f.write('last update: '+nowstr + '\n')
    f.close()




# create output directories    
def create_output_dirs(opath):
    if not os.path.exists(opath):
        os.mkdir(opath)

    dump_path = opath+'dump/'
    proc_path = opath + 'processed-tables/'

    if not os.path.exists(dump_path):
        os.mkdir(dump_path)    
    if not os.path.exists(proc_path):
        os.mkdir(proc_path)
    return dump_path,proc_path
    
def JoinSerotipeTables(dump_path):
    sero1 = dump_path+'Serologia.csv'
    sero2 = dump_path+'Serolog\xc3\xada2.csv'
    s1 = pd.read_csv(sero1)
    s1.set_index('HistoriaClinica',inplace= True)

    s2 = pd.read_csv(sero2)
    s2.set_index('HistoriaClinica',inplace=True)

    serototal = pd.concat([s1,s2],axis = 1)

    serototal.to_csv(dump_path+'Serologias.csv')
    subprocess.call(['rm',sero1])
    subprocess.call(['rm',sero2])

def get_codefiles(dump_path):
    codefiles = glob.glob(dump_path+'*[{c,C}]ode*csv')
    codepath = dump_path+'codefiles/'
    if not os.path.exists(codepath):
        os.mkdir(codepath)
    for f in codefiles:
        subprocess.call(['cp',f,codepath])
    return codefiles


##########################################
#### internal functions for parse_raw_data
##########################################
def remove_numbers(s):
    return(''.join([i for i in s if not i.isdigit()]))

def remove_last_two_characters(s):
    return s[:-2]

def get_last_two_characters(s):
    return s[-2:]


def load_data(inputfile):
    data = pd.read_csv(inputfile)
    primary = data.columns[0] 
    data.set_index(primary,inplace = True)
    return(data)
    

## detecto numero de visitas de la tabla    
def get_visitas(data,tabla,column_clases):
    if(tabla == 'EvAdversos'):
        nmax =  int(data.shape[1])/int(len(column_clases)-1)
        n_visita = [str(i+1).zfill(1) for i in range(nmax)]
    else:
        nmax =  int(data.shape[1])/int(len(column_clases)-1)
        n_visita = [str(i).zfill(1) for i in range(nmax-1)]
    return(n_visita)


def broad_to_long(table,column_clases,n_visita,dropna = True):
    long_format = []
    cols = pd.Series(table.columns)

    for n in n_visita:
        visita_ith = [c+n for c in column_clases]
        index = range(len(visita_ith))
        
        #indice de columnas que sobreviven
        ii = [i for i in index if visita_ith[i] in cols.values]
        visit_i = pd.Series(visita_ith)[ii]
        newc = pd.Series(column_clases)[ii]
        
        daux =  table[visit_i]
        daux.columns = newc
        daux['numero_visita'] = n
        long_format.append(daux)         
    long_format = pd.concat(long_format)
    
    if dropna:
        long_format.dropna(subset=column_clases,inplace = True,how='all')
    
    return(long_format)


##########################################
##########################################



def parse_raw_data(tablename, tablefile,proc_path):
    col_dict = {  # this dictionary define columns to be parsed in each table. 
    'Cardio': ['Ecg', 'FechaCardio', 'ECGDescrip', 'Eco', 'FechaEco',
                'Ecodescrip'],

    'Clinica': ['ExClinico', 'Piel', 'Ojo', 'ORL', 'Muculo', 'Cardio', 'Resp',
                'Gastro', 'Higado', 'SNC', 'Metabol', 'Endoc', 'Uro', 'Hemato',
                'Otros'],

    'EvAdversos': ['Ev', 'NumVisitaEV', 'CodigoEA', 'quetto', 'DescripEA', 'InicioEA',
                'FinalEA', 'SeveridadEA', 'RelacionEA', 'TratEA', 'EvolEA'],

    'Laboratorio': ['Lab', 'LabGral', 'Hb', 'Hto', 'Blancos', 'Cayados', 'Neutrofilos',
                'Eos', 'Bas', 'Linfo', 'Mono', 'Plaquetas', 'Bitotal', 'Bidirecta',
                'TGO', 'TGP', 'Proteinas', 'Albumina', 'Colesterol', 'Falcalina',
                'Creatinina'],
                
    'Parasitemia': ['FechaPar', 'Mh', 'Pcr', 'Xeno', 'IRL', 'Hemoc','Parasit','Tecnica'], 

    'Serologias': ['Serologia', 'Elisa', 'TitElisa', 'Hai', 'TituloHai', 'AD',
                'TitAD', 'AP', 'TitAP', 'F23', 'TitF23', 'Antiidiotipo'],
            
    }
    data = load_data(tablefile)    
    column_clases = col_dict[tablename]
    n_visita = get_visitas(data,tablename,column_clases)
    longtable = broad_to_long(data,column_clases,n_visita,dropna = True)
    
    return longtable




#this function requiere parse_raw_data function
def process_tables(dump_path,proc_path):
    results = {}
    tables = ['Serologias','Laboratorio','Clinica','EvAdversos','Parasitemia','Cardio','Demografico','Pacientes','Tratamiento']
    tables_pass_true = ['Demografico','Tratamiento','Pacientes']

    for tablename in tables:
        tablefile = dump_path + tablename + '.csv'
        if tablename not in tables_pass_true:
            processedtable = parse_raw_data(tablename = tablename,tablefile = tablefile,proc_path = proc_path)
            processedtable.reset_index(inplace = True)
            results.update({tablename:processedtable})
        
        else:
            processedtable = pd.read_csv(tablefile)
            results.update({tablename:processedtable})
            results.update({tablename:processedtable})
    return results
    
################## WORK HERE!! ######################    
# input table in dataframe format previously preprocessed, i.e in "longformat" having a "numero_visita" column    
def postprocessing(tablename,longtable):
    if tablename == 'Parasitemia':
        longtable.Tecnica.replace({'PCR':'Pcr'},inplace = True)
        dumm = pd.get_dummies(longtable,columns=['Tecnica'])
        dumm.Xeno.fillna(0,inplace = True) # esto para poder sumar luego 
        dumm.Pcr.fillna(0,inplace = True)
        
        aux_Pcr = dumm.Parasit * dumm.Tecnica_Pcr
        aux_Xeno = dumm.Parasit * dumm.Tecnica_Xeno
        aux_Pcr.fillna(0,inplace = True)
        aux_Xeno.fillna(0,inplace = True)

        dumm['Pcr'] = dumm.Pcr + aux_Pcr
        dumm['Xeno'] = dumm.Xeno + aux_Xeno
        dumm['Tecnica'] = longtable.Tecnica
        dumm.drop(['Tecnica_Pcr','Tecnica_Xeno'],axis = 1,inplace = True)
        postprocessed = dumm.copy()
        return postprocessed
    else:
        return longtable 


def savetable(tablename, table, proc_path):
    tablefile = dump_path + tablename + '.csv'
    output_table_file = proc_path + tablename + '.csv'
    table.to_csv(output_table_file,sep = '|',encoding='utf-8',index = False)    


if __name__ == '__main__' : 
    args = get_args()
    input_db, opath = args.input_db, args.opath
    dump_path,proc_path =  create_output_dirs(opath)
    print_date(opath) # documment running date.
    
    #this function dump the entire db in sql script and tablee by table in csv format
    #the output is downstream opath, in dump folder
    DumpDb(input_db,dump_path)    
    

    #esto reemplaza el scrppython join_sertotipe_tables.py 
    JoinSerotipeTables(dump_path)

    #code_files: detect and save:
    codefiles = get_codefiles(dump_path)
    
    processedtables = process_tables(dump_path,proc_path)  #return a dictionary with tables
    
            
    ## save each table in a different file
    for tablename in processedtables.keys():
        table = processedtables[tablename]
        final_table = postprocessing(tablename,longtable=table)
        savetable(tablename, final_table, proc_path)    
    
    




