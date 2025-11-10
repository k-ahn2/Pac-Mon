import React, { useState, useRef, useEffect, useContext } from 'react'
import localApiSource from '../source/localApiSource.json'
import * as env from '../env/env.js'

export const ApiContext = React.createContext({
  getTraces: () => {},
  traces: {},
  recordCount: null,
  donwloadedRecordCount: null
})

export const ApiProvider = ({ children }) => {

  const [traces, setTraces] = useState([])
  const tracePages = useRef([])
  const [recordCount, setRecordCount] = useState(0)
  const [donwloadedRecordCount, setDownloadedRecordCount] = useState(0)
  const counter = useRef(0)
  const localRecordCount = useRef(0)

  useEffect(() => {
    //setApiReponse(localApiSource)
    //getNodes()
    // queryApi()
    console.log((200/2000)*100)
  },[])

  const getNodes = async () => {
    const api = new URL(env.NODES_API_URL)
    const options = {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json;charset=UTF-8",
      }
    };
    
    fetch(api, options)
      .then((response) => response.json())
      .then((data) => {
        console.log(data)
        console.log(data.filter(node => node.lastUpEvent !== null && node.callsign.length >= 3));
      });
  }

  const getTraces = async (queryParams) => {

    const tempTraces = []

    const api = new URL(env.TRACES_API_URL)
    api.search = queryParams

    console.log(api)

    const options = {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json;charset=UTF-8",
      }
    };
    
    const fetchTraces = (cursor = null) => {
      
      if (!cursor) {
     
        fetch(api, options)
        .then((response) => response.json())
        .then((data) => {
          counter.current = 1 
          tracePages.current = [...data.data]
          // First fetch - update state to display the data received
          localRecordCount.current = data.page.totalCount
          setRecordCount(data.page.totalCount)
          setTraces(tracePages.current)
          data.page.totalCount > env.API_PAGE_SIZE ? setDownloadedRecordCount(counter.current * env.API_PAGE_SIZE) : setDownloadedRecordCount(data.page.totalCount)
          // If there is a cursor, loop
          if (data.page.next) fetchTraces(data.page.next)
        });

      } else {
        queryParams.set("cursor", cursor)
        api.search = queryParams
        
        fetch(api, options)
        .then((response) => response.json())
        .then((data) => {
          counter.current += 1  
          tracePages.current = [...tracePages.current, ...data.data]
          console.log('Fetching Page', counter.current)
          if (data.page.next) {
            setDownloadedRecordCount(counter.current * env.API_PAGE_SIZE)
            console.log(((counter.current * env.API_PAGE_SIZE)/localRecordCount.current)*100)
            fetchTraces(data.page.next)
          } else {
            console.log('finshed', recordCount, tracePages.current.length)
            setDownloadedRecordCount(localRecordCount.current)
            setTraces(tracePages.current)
            tracePages.current = []
          }
        });

      }

    }

    fetchTraces()

  }
 
  const contextValues = { 
    traces,
    getTraces,
    recordCount,
    donwloadedRecordCount
  }

  return (
    <ApiContext.Provider value={contextValues}>
      {children}
    </ApiContext.Provider>
  )
}