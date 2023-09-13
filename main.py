import streamlit as st

import json
import http.cookiejar
import urllib.request

from datetime import datetime
from datetime import timedelta

import yfinance

import pandas as pd
import numpy as np

def loadJson(i):
  cookie_jar = http.cookiejar.CookieJar()
  opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
  opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201'),
                        ('Accept', 'text/html, text/plain, text/css, text/sgml, */*;q=0.01')]
  # Pega o histórico de Dividend Yield...
  # Últimos 5 anos...
  # https://statusinvest.com.br/acao/companytickerprovents?ticker=TRPL4&chartProventsType=1
  url = f'https://statusinvest.com.br/acao/companytickerprovents?ticker={i}&chartProventsType=1'
  with opener.open(url) as link:
    company_indicators = link.read().decode('ISO-8859-1')
  return json.loads(company_indicators)

def ArrumaData(dia, data):
  while dia != 'Friday':
    data = data - timedelta(days=1)
    dia = pd.to_datetime(data, dayfirst=True).strftime('%A')
  return data

def ativosb3():
  file = open("ativosb3.txt")
  lista_Teste = []
  while file:
    line = file.readline()
    lista_Teste.append(line.replace('\n', ''))
    if line == "":
        break
  return lista_Teste

def dates_now():
  date_now = datetime.date(datetime.now())
  date_now_Day = pd.to_datetime(date_now, dayfirst=True).strftime('%A')
  date_now_Month = pd.to_datetime(date_now, dayfirst=True).strftime('%B')
  return date_now, date_now_Day, date_now_Month

def yestarday(date_now, date_now_Day):
  if date_now_Day == 'Monday' or date_now_Day == 'Sunday' or date_now_Day == 'Saturday':
    yesterday = (ArrumaData(date_now_Day, date_now)).strftime('%Y-%m-%d')
  else:
    yesterday = (date_now - timedelta(days=1)).strftime('%Y-%m-%d')
  return yesterday

def session_init():
  st.session_state['namepage'] = 'Dividendo Inteligente'
  st.session_state['listEmpresas'] = []
  st.session_state['listEmpresas_SA'] = []
  st.session_state['extractAll'] = []
  st.session_state['listAnuncia'] = []
  st.session_state['date_dy'] = []
  st.session_state['dy_media'] = []
  st.session_state['lista_Ativos_SA'] = []
  st.session_state['conjunto_date_dy'] = []
  st.set_page_config(page_title=st.session_state['namepage'], 
                        layout='centered', 
                        initial_sidebar_state='collapsed', 
                        menu_items=None)
  st.title(st.session_state['namepage'])
  st.session_state['div_desejado'] = st.sidebar.slider('Dividendo Desejado', min_value=0, max_value=100, value=6)
  st.session_state['ultimos_anos'] = st.sidebar.slider('Quantos Anos de Histórico de Dividendos', min_value=0, max_value=5, value=5)

if __name__ == "__main__":
  session_init()
  with st.form(key='my_form'):
    lista_Ativos = st.multiselect('Selecione os ativos', ativosb3())
    ok = st.form_submit_button('Confirmar')
    with st.spinner("Um momento..."):
      if ok:
        date_now, date_now_Day, date_now_Month = dates_now()
        for i in lista_Ativos:
          st.session_state['lista_Ativos_SA'].append(i+'.SA')

        for i in lista_Ativos:
          st.session_state['date_dy'] = []
          company_indicators = loadJson(i)
          company_indicators_dy = company_indicators['assetEarningsModels']
          for i in company_indicators_dy:
            st.session_state['date_dy'].append(i.get('ed'))

          date_dy_config = pd.to_datetime(st.session_state['date_dy'], dayfirst=True).strftime('%B')
          fdist=dict(zip(*np.unique(date_dy_config, return_counts=True)))
          st.session_state['conjunto_date_dy'].append(fdist)

        for cont_conjunto_date_dy, i in enumerate(st.session_state['conjunto_date_dy']):
          if date_now_Month in i.keys():
            st.session_state['listAnuncia'].append('Sim')
          else:
            st.session_state['listAnuncia'].append('Não')
          st.session_state['listEmpresas'].append(lista_Ativos[cont_conjunto_date_dy])

        for i in st.session_state['listEmpresas']:
          st.session_state['listEmpresas_SA'].append(i+'.SA')

        listEmpresasDownload = yfinance.download(st.session_state['lista_Ativos_SA'], start = yestarday(date_now, date_now_Day), end = date_now)['Close']

        for cont_listEmpresas, i in enumerate(st.session_state['listEmpresas']):
          st.session_state['dy_media'] = []
          company_indicators = loadJson(i)
          company_indicators_media = company_indicators['assetEarningsYearlyModels'][-(st.session_state['ultimos_anos']):]
          for cont_company_indicators_media, i in enumerate(company_indicators_media):
            st.session_state['dy_media'].append(company_indicators_media[cont_company_indicators_media].get('value'))

          avg = sum(st.session_state['dy_media']) / len(st.session_state['dy_media'])
          precoTeto = avg/(st.session_state['div_desejado']/100) 
          if len(st.session_state['listEmpresas']) == 1:
            value = listEmpresasDownload.iloc[0]
          else:
            value = listEmpresasDownload[st.session_state['listEmpresas_SA'][cont_listEmpresas]].iloc[0]

          extract = {}
          extract['Ativo'] = st.session_state['listEmpresas'][cont_listEmpresas]
          extract['Media DY Últimos Anos'] = "R$%.2f" % round(avg, 2)
          extract['Preco Teto'] = "R$%.2f" % round(precoTeto, 2)
          extract['Cotação Atual'] = "R$%.2f" % round(value, 2)
          extract['Status Compra'] = 'Sim' if value < precoTeto else 'Não'
          extract['Costuma Anunciar esse Mês'] = st.session_state['listAnuncia'][cont_listEmpresas]
          st.session_state['extractAll'].append(extract)

        st.table(st.session_state['extractAll'])

