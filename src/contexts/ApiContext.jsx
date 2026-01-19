import React, { useState, useRef } from 'react'
import * as env from '../env/env.js'

export const ApiContext = React.createContext({
  getTraces: () => {},
  setRoutingInfoOnly: () => {},
  routingInfoOnly: false,
  traces: {},
  recordCount: null,
  donwloadedRecordCount: null
})

export const ApiProvider = ({ children }) => {

  // Used whilst fetching traces, locally within the API Context
  const tracePages = useRef([]) // Used to store pages of traces during fetching
  const localRecordCount = useRef(0) // Used to store the total record count during fetching
  const counter = useRef(0) // Used to count the number of pages fetched
  
  // Context state variables for traces and record counts
  const [traces, setTraces] = useState([]) // All traces fetched from the API
  const [routingInfoOnly, setRoutingInfoOnly] = useState(false);
  const [recordCount, setRecordCount] = useState(0) // Total number of records available from the API
  const [donwloadedRecordCount, setDownloadedRecordCount] = useState(0) // Number of records downloaded so far
  
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

    let api;
    // Set the URL based on L2 or L3 traces
    if (routingInfoOnly && queryParams.get("l3type") === "Routing info") {
      api = new URL(env.L3_TRACES_API_URL)
    } else {
      api = new URL(env.TRACES_API_URL)
    }

    api.search = queryParams

    const options = {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json;charset=UTF-8",
      }
    };
    
    const fetchTraces = (cursor = null) => {
      
      if (!cursor) {
        // First fetch - no cursor
        fetch(api, options).then((response) => response.json()).then((data) => {
          
          counter.current = 1
          tracePages.current = [...data.data] 
          localRecordCount.current = data.page.totalCount
          setRecordCount(data.page.totalCount)
          setTraces(tracePages.current)
          data.page.totalCount > env.API_PAGE_SIZE ? setDownloadedRecordCount(counter.current * env.API_PAGE_SIZE) : setDownloadedRecordCount(data.page.totalCount)
          if (data.page.next) fetchTraces(data.page.next) // If there is a cursor, loop

        });

      } else {
        // Subsequent fetches - use cursor
        queryParams.set("cursor", cursor)
        api.search = queryParams
        
        fetch(api, options).then((response) => response.json()).then((data) => {

          console.log('Fetched Page', counter.current)

          // Increment page counter and check if max download size reached
          counter.current += 1 
          if (counter.current * env.API_PAGE_SIZE > env.MAX_PERMITTED_DOWNLOAD_SIZE) {
            setTraces(tracePages.current)
            return
          }
          
          tracePages.current = [...tracePages.current, ...data.data]
          
          if (data.page.next) {
            setDownloadedRecordCount(counter.current * env.API_PAGE_SIZE)
            console.log(((counter.current * env.API_PAGE_SIZE)/localRecordCount.current)*100)
            fetchTraces(data.page.next)
          } else {
            console.log('Finshed', recordCount, tracePages.current.length)
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
    setRoutingInfoOnly,
    routingInfoOnly,
    recordCount,
    donwloadedRecordCount
  }

  return (
    <ApiContext.Provider value={contextValues}>
      {children}
    </ApiContext.Provider>
  )
}