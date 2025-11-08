import React, { useState, useRef, useEffect, useContext } from 'react'
import localApiSource from '../source/localApiSource.json'
import * as env from '../env/env.js'

export const ApiContext = React.createContext({
  getTraces: () => {},
  traces: {},
  recordCount: null
})

export const ApiProvider = ({ children }) => {

  const [traces, setTraces] = useState([])
  const [recordCount, setRecordCount] = useState(null)

  useEffect(() => {
    //setApiReponse(localApiSource)
    //getNodes()
    // queryApi()
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
    
    fetch(api, options)
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
        setTraces(data.data)
        setRecordCount(data.page.totalCount)
      });

  }
 
  const contextValues = { 
    traces,
    getTraces,
    recordCount
  }

  return (
    <ApiContext.Provider value={contextValues}>
      {children}
    </ApiContext.Provider>
  )
}