import pandas as pd
import math
import sys

rangos = [0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.5, 0.60, 0.70, 0.80, 0.90, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3, 100]
rangosVE = [0, 1, 2, 3, 4, 5, 100]

def CalcularSuma(intervalo, consumos):
    total = 0
    cont = 0
    i = 0
    while i<len(consumos):
        if consumos[i] in intervalo:
            #print("Valor en intervalo (%s): %3.3f" % (intervalo, consumos[i]))
            total += consumos[i] 
            cont += 1
        i += 1
    return total

def CalcularMedia(intervalo, consumos):
    total = 0
    cont = 0
    i = 0
    while i<len(consumos):
        if consumos[i] in intervalo:
            #print("Valor en intervalo (%s): %3.3f" % (intervalo, consumos[i]))
            total += consumos[i] 
            cont += 1
        i += 1
    return total/cont

def SumarConsumosMinimos(minimo, consumos):
    total = 0
    i = 0
    while i<24:
        if consumos[i] < minimo:
            total += consumos[i] 
        else:
            total += minimo       
        i += 1
    return total

#media>0 significa segunda ronda del algoritmo, con un consumo medio del mes ya calculado después de la primera ronda
def ProcesarDia(consumos, media):
    segundaVuelta = media>0 
    data = pd.Series(consumos) 
    frec = data.value_counts(bins = rangos)

    df = frec.rename_axis('Intervalos').reset_index(name='Frecuencia').sort_values(['Intervalos'], ascending=True)

    intervalos = df['Intervalos'].tolist()
    frecuencia = df['Frecuencia'].tolist()
    
    #print(df)
    
    consumoMinimoTotal = 0
    hayFV = False
    found = False
    minimo = 100
    cortes = 0
    i = 0
    while (i < len(intervalos)) and (not found):
        intervalo = df['Intervalos'].tolist()[i] 
        
        if i==0: #primer intervalo de 0 a 50 Wh
            if frecuencia[i]>0: 
                if frecuencia[i]<=2: #Posible corte de luz y no FV
                    cortes += 1
                if frecuencia[i]>2: #Posible detección FV
                    hayFV = True
        else:
            if frecuencia[i]>=2 and intervalo.mid<minimo:
                minimo = intervalo.mid #Tomamos este valor como valor mínimo fuera del primer intervalo 0, por si no encontraramos ninguna agrupación de valores
            if frecuencia[i]>=2: #Posible consumo neveras
                minimo = CalcularMedia(intervalo, consumos)
                if (segundaVuelta>0) and (minimo>(media*1.10)): #dejamos un margen de un 10% más de la media
                    minimo = media #corrección (el mínimo calculado es muy alto. Igual todo el día con AA, por ejemplo)
                if hayFV and (segundaVuelta>0) and (minimo<(media*0.9)): #dejamos un margen de un 10% menos de la media
                    minimo = media #corrección (el mínimo calculado es muy bajo. Esto suele ser por FV, por ejemplo)
                found = True
                
        i += 1
        
    #Llegados a este punto tenemos el consumo mínimo medio detectado, pero falta calcular la suma de consumos mínimos, y si hay FV se sumará solo la parte que haya de consumo
    if found:
        consumoMinimoTotal = SumarConsumosMinimos(minimo, consumos)
        
    #Ahora vamos a calcular si hay carga de VE de madrugada
    consumoPorVE = 0
    if not segundaVuelta: #para calcular esto solo una vez, de momento
        consumosPrimerasHoras = consumos[0:8]
        data = pd.Series(consumosPrimerasHoras) 
        frec = data.value_counts(bins = rangosVE)

        df = frec.rename_axis('Intervalos').reset_index(name='Frecuencia').sort_values(['Intervalos'], ascending=True)
        intervalos = df['Intervalos'].tolist()
        frecuencia = df['Frecuencia'].tolist()
        
        i = len(intervalos)-1
        while (i >=0 ) and (consumoPorVE==0):
            intervalo = df['Intervalos'].tolist()[i] 
            if frecuencia[i]>2 and intervalo.left>3: #más de 3 kW de madrugada y más de 3 veces??? --> candidato a VE
                consumoPorVE = CalcularSuma(intervalo, consumos)
                    
            i -= 1
                    
    return found, minimo, consumoMinimoTotal, sum(consumos), consumoPorVE, cortes, hayFV

#Pendiente 1: Controlar si llegan los argumentos
filename = sys.argv[1]

#Pendiente 2: Controlar si llegan días completos
df = pd.read_csv(filename,
            delimiter=';',
            dayfirst=True,
            header=0,
            decimal=',',
            names=['CUPS', 'Fecha', 'Hora', 'Consumo_kWh', 'Metodo_obtencion'])

found= False
consumoVE = 0
cortes = 0
totalCortes = 0
hayFV = 0
diasFV = 0
totalDias = 0
consumoTotalVE = 0
consumoMinimo=0
consumoTotal=0
consumoMinimoTotal=0
listaConsumosMinimosPorHora = []
media = 0
i = 0
lista = df['Consumo_kWh'].tolist()

#Primer cálculo aproximado
while i+24 <= len(lista):
    datosDia = lista[i:i+24]
    ultimodia = float(datosDia[23])
    if math.isnan(ultimodia):
        print('Datos incompletos')
    else:
        found, consumoMinimoPorHora, consumoMinimo, total, consumoVE, cortes, hayFV = ProcesarDia(datosDia, media)
        #print("Dia %d: Consumos neveras mínimo-->Diario/Total %3.3f-->%3.1f/%3.1f (%1.1f%%)  - VE: %3.1f" % (i/24+1, consumoMinimoPorHora, consumoMinimo, total, consumoMinimo*100/total, consumoVE))
        if found:
            listaConsumosMinimosPorHora.append(consumoMinimoPorHora)
            consumoMinimoTotal += consumoMinimo
        consumoTotalVE += consumoVE
        totalCortes += cortes
        if hayFV:
            diasFV += 1
        consumoTotal += total
    i += 24
    totalDias += 1

print("\nAnálisis realizado sobre %d días (%d meses):" % (totalDias, totalDias/30))
diasEncontrados= len(listaConsumosMinimosPorHora)
if diasEncontrados<totalDias:
    if hayFV:
        print("No se han podido encontrar el consumo mínimo permanente para %d/%d días, probablemente debido a que hay FV con baterías instaladas" %(totalDias-diasEncontrados, totalDias))
    else:
        print("No se han podido encontrar el consumo mínimo permanente para %d/%d días" %(totalDias-diasEncontrados, totalDias))

#Segundo cálculo más aproximado, teniendo en cuenta los datos de la primera vuelta
if consumoTotal==0:
    print('No hay datos suficientes para realizar el cálculo')
else:
    print("Primera vuelta: Consumos Permanentes --> Mínimo: %3.3f, Diario: %3.1f kWh/día, Acumulado/Total: %3.1f/%3.1f (%1.1f%%)" % (sum(listaConsumosMinimosPorHora)/len(listaConsumosMinimosPorHora), consumoMinimoTotal/totalDias, consumoMinimoTotal, consumoTotal, consumoMinimoTotal*100/consumoTotal))

    #Ahora segunda vuelta, usando la media de los consumos con más frecuencia
    data = pd.Series(listaConsumosMinimosPorHora) 
    frec = data.value_counts(bins = rangos)
    df = frec.rename_axis('Intervalos').reset_index(name='Frecuencia')
    intervalos = df['Intervalos'].tolist()
    media = CalcularMedia(df['Intervalos'].tolist()[0], listaConsumosMinimosPorHora)
    
    print("Media valores mínimos primera vuelta: %3.3f" % (media))

    consumoMinimo=0
    consumoTotal=0
    consumoMinimoTotal=0
    listaConsumosMinimosPorHora = []
    listaConsumosMinimosSinVECadaDia = []
    i = 0

    while i+24 <= len(lista):
        datosDia = lista[i:i+24]
        ultimodia = float(datosDia[23])
        found, consumoMinimoPorHora, consumoMinimo, total, consumoVE, cortes, hayFV = ProcesarDia(datosDia, media)
        #print("Dia %d: Consumos neveras mínimo/24h-->Diario/Total %3.3f/%3.1f-->%3.1f/%3.1f (%1.1f%%)  - VE: %3.1f" % (i/24+1, consumoMinimoPorHora, consumoMinimoPorHora*24, consumoMinimo, total, consumoMinimo*100/total, consumoVE))
        if found:
            listaConsumosMinimosPorHora.append(consumoMinimoPorHora)
            consumoMinimoTotal += consumoMinimo
        consumoTotal += total
        i += 24

    #Resultados
    if consumoTotal>0:
        print("Segunda vuelta: Consumos Permanentes --> Mínimo: %3.3f, Diario: %3.1f kWh/día, Diario sin FV: %3.1f kWh/día, Acumulado/Total: %3.1f/%3.1f (%1.1f%%)" % (sum(listaConsumosMinimosPorHora)/len(listaConsumosMinimosPorHora), consumoMinimoTotal/totalDias, sum(listaConsumosMinimosPorHora)*24/totalDias, consumoMinimoTotal, consumoTotal, consumoMinimoTotal*100/consumoTotal))
    if consumoTotalVE>30:
        print("Consumo por VE = %3.1f" % (consumoTotalVE))
    elif consumoTotalVE>10:
        print("Posible consumo puntual por VE? Total = %3.1f" % (consumoTotalVE))
    if totalCortes>0:
        print("Se han detectado %d posibles cortes de corriente" % (totalCortes))
    else:
        print("No se han detectado cortes de corriente")
    if diasFV>(totalDias/2):
        print("Instalación FV detectada")

