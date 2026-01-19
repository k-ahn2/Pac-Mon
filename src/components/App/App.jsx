// React & Pac-Mon
import { useState, useContext, useEffect, useRef } from 'react'
import { ApiContext } from '../../contexts/ApiContext'
import Trace from '../Trace/Trace';
import * as env from '../../env/env'
import './App.css'
import appIcon from '../../images/pacmon.png'
// Bootstrap
import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';
import Image from 'react-bootstrap/Image';
import { Col, Row } from 'react-bootstrap';
import Badge from 'react-bootstrap/Badge';
import { Form, Modal } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
// MUI
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import Chip from '@mui/material/Chip';
// Other
import moment from 'moment';
import 'moment/locale/en-gb';
import JSONPretty from 'react-json-pretty';

function App() {

  const { 
      getTraces,
      setRoutingInfoOnly,
      routingInfoOnly,
      traces,
      recordCount,
      donwloadedRecordCount
  } = useContext(ApiContext);

  // API Filter States
  const [showJson, setShowJson] = useState(false)
  const [showAlert, setShowAlert] = useState(false)
  const [traceReportFrom, setTraceReportFrom] = useState('MB7NPW,GB7NBH');
  const [traceStart, setTraceStart] = useState(null);
  const [traceEnd, setTraceEnd] = useState(null);
  
  // Local Filter States
  const iteratingLocalFilter = useRef([])

  const [suppressNodes, setSuppressNodes] = useState(true)
  const [suppressUI, setSuppressUI] = useState(true)
  const [suppressNetRom, setSuppressNetRom] = useState(false)
  const [suppressInp3, setSuppressInp3] = useState(false)
  const [showSequenceCounters, setShowSequenceCounters] = useState(false)
  const [showPayLen, setShowPayLen] = useState(false)
  const [showNetRomDetails, setShowNetRomDetails] = useState(false)
  const [showOnlyFRMR, setShowOnlyFRMR] = useState(false)
  const [showOnlyRoutingInfo, setShowOnlyRoutingInfo] = useState(false)
  
  const [selectedNetRomCircuits, setSelectedNetRomCircuits] = useState([])
  const [selectedPorts, setSelectedPorts] = useState([])
  const [selectedL2Callsigns, setSelectedL2Callsigns] = useState([])
  
  // Data States
  const [filteredTraces, setFilteredTraces] = useState([]);
  const [seenNetRomCircuits, setSeenNetRomCircuits] = useState([]);
  const [seenL2Callsigns, setSeenL2Callsigns] = useState([]);
  const [seenPorts, setSeenPorts] = useState([]);

  // Search Hides
  const [toggleApiSearch, setToggleApiSearch] = useState(false);
  const [toggleFilters, setToggleFilters] = useState(false);
  
  // Re-run the filter if any of the local filter states change
  useEffect(() => {
    if (traces.length == 0) return
    regenerateURL()
    filterTraces()
  }, [traces, 
      selectedNetRomCircuits, 
      selectedPorts,
      selectedL2Callsigns, 
      suppressNodes, 
      suppressUI, 
      suppressNetRom, 
      suppressInp3,
      showOnlyFRMR,
      showOnlyRoutingInfo
  ]);

  useEffect(() => {
    if (!traceStart || !traceEnd) return
    regenerateURL()
  }, [showSequenceCounters, 
      showPayLen, 
      showNetRomDetails 
  ]);

  useEffect(() => {
      
      // URL Search Params
      
      // rf = reportFrom
      // ts = traceStart
      // te = traceEnd

      // sl2 = selectedL2Callsigns
      // sp = selectedPorts
      // snr = selectedNetRomCircuits
      
      // sun = suppressNodes
      // suui = suppressUI
      // sunr = suppressNetRom
      // sui3 = suppressInp3
      // shsc = showSequenceCounters
      // shpl = showPayloadLength
      // snrd = showNetRomDetails
    
      const urlParams = new URLSearchParams(document.location.search);
      
      const urlTraceStart = moment(urlParams.get('ts'))
      const urlTraceEnd = moment(urlParams.get('te'))
      const urlReportFrom = urlParams.get('rf')
      
      const urlSelectedL2 = urlParams.getAll('sl2')
      const urlSelectedPorts = urlParams.getAll('sp')
      const urlSelectedNetRom = urlParams.getAll('snr')
      
      const urlSuppressNodes = urlParams.get('sun')
      const urlSuppressUI = urlParams.get('suui')
      const urlSuppressNetRom = urlParams.get('sunr')
      const urlSuppressInp3 = urlParams.get('sui3')
      const urlShowSequenceCounters = urlParams.get('shsc')
      const urlShowPayloadLength = urlParams.get('shpl')
      const urlShowNetRomDetails = urlParams.get('snrd')
      const urlShowOnlyRoutingInfo = urlParams.get('shori')

      if (urlTraceStart.isValid()) {
        setTraceStart(urlTraceStart)
      } else {
        setTraceStart(moment().subtract(15,'minutes'))
      }

      if (urlTraceEnd.isValid()) {
        setTraceEnd(urlTraceEnd)
      } else {
        setTraceEnd(moment())
      }

      if (urlReportFrom) setTraceReportFrom(urlReportFrom)

      if (urlSelectedL2.length > 0) {
        
        const urlSeenL2Array = urlSelectedL2.map(l2Pair => { 
          const l2PairArray = l2Pair.split(',')
          if (l2PairArray.length == 2) return l2PairArray
        })
      
        setSelectedL2Callsigns(urlSeenL2Array)
        setSeenL2Callsigns(urlSeenL2Array)
      }

      if (urlSelectedPorts.length > 0) {
        
        const urlSelectedPortsArray = urlSelectedPorts.map(selectedPort => { 
          const portAndCallsignObject = selectedPort.split(',')
          if (portAndCallsignObject.length == 2) {
            return {
              port: portAndCallsignObject[0],
              reportFrom: portAndCallsignObject[1]
            }
          }
        })

        setSelectedPorts(urlSelectedPortsArray)
      }

      if (urlSelectedNetRom.length > 0) {
        
        const urlSelectedNetRomArray = urlSelectedNetRom.map(netRomCctAndCallsigns => { 
          const netRomCctAndCallsignsArray = netRomCctAndCallsigns.split(',')
          if (netRomCctAndCallsignsArray.length == 3) {
            return {
              toCct: netRomCctAndCallsignsArray[0],
              l3src: netRomCctAndCallsignsArray[1],
              l3dst: netRomCctAndCallsignsArray[2]
            }
          }
        })

        setSelectedNetRomCircuits(urlSelectedNetRomArray)
      }

      console.log(urlSuppressNetRom)

      if (urlShowNetRomDetails) setShowNetRomDetails(urlShowNetRomDetails == 'true' ? true : false)
      if (urlSuppressNodes) setSuppressNodes(urlSuppressNodes == 'true' ? true : false)
      if (urlSuppressUI) setSuppressUI(urlSuppressUI == 'true' ? true : false)
      if (urlSuppressNetRom) setSuppressNetRom(urlSuppressNetRom == 'true' ? true : false)
      if (urlSuppressInp3) setSuppressInp3(urlSuppressInp3 == 'true' ? true : false)
      if (urlShowSequenceCounters) setShowSequenceCounters(urlShowSequenceCounters == 'true' ? true : false)
      if (urlShowPayloadLength) setShowPayLen(urlShowPayloadLength == 'true' ? true : false)
      if (urlShowOnlyRoutingInfo) setShowOnlyRoutingInfo(urlShowOnlyRoutingInfo == 'true' ? true : false)

  }, []);

  const regenerateURL = () => {
    const api = new URL(window.location.href)    
    const queryParams = new URLSearchParams();

    queryParams.append("rf", traceReportFrom)
    queryParams.append("ts", traceStart.format('YYYY-MM-DD[T]HH:mm:ss[Z]'))
    queryParams.append("te", traceEnd.format('YYYY-MM-DD[T]HH:mm:ss[Z]'))
    
    selectedL2Callsigns.map(l2PairArray => {
       queryParams.append("sl2", l2PairArray.join(','))
    })

    selectedPorts.map(selectedPort => {
      const selectedPortString = `${selectedPort.port},${selectedPort.reportFrom}`
      queryParams.append("sp", selectedPortString)
    })

    selectedNetRomCircuits.map(netRomCctAndCallsigns => {
      const netRomCctAndCallsignsString = `${netRomCctAndCallsigns.toCct},${netRomCctAndCallsigns.l3src},${netRomCctAndCallsigns.l3dst}`
      queryParams.append("snr", netRomCctAndCallsignsString)
    })

    if (suppressNodes) queryParams.append("sun", suppressNodes)
    if (suppressUI) queryParams.append("suui", suppressUI)
    if (suppressNetRom) queryParams.append("sunr", suppressNetRom)
    if (suppressInp3) queryParams.append("sui3", suppressInp3)
    if (showSequenceCounters) queryParams.append("shsc", showSequenceCounters)
    if (showPayLen) queryParams.append("shpl", showPayLen)
    if (showNetRomDetails) queryParams.append("snrd", showNetRomDetails)
    if (showOnlyRoutingInfo) queryParams.append("shori", showOnlyRoutingInfo)

    api.search = queryParams
    window.history.pushState('', '', api)
  }

  const findSeenCallsignsAndNetRom = () => {

    const tmpSeenCcts = []
    const tmpSeenPorts = []
    const tmpSeenL2Callsigns = []

    traces.map(t => {
      
      if (t.report.ptcl == 'NET/ROM' && t.report.toCct) {
        
        // Add NET/ROM circuits
        const circuitObject = {}
        circuitObject.toCct = t.report.toCct
        circuitObject.l3src = t.report.l3src
        circuitObject.l3dst = t.report.l3dst

        if (tmpSeenCcts.filter(c => JSON.stringify(c) === JSON.stringify(circuitObject)).length == 0) {
          tmpSeenCcts.push(circuitObject)
        }        

        setSeenNetRomCircuits(tmpSeenCcts.sort((a,b) => a.toCct - b.toCct))
      }

      // Add Ports
      const portObject = {}
      portObject.port = t.report.port
      portObject.reportFrom = t.report.reportFrom

      if (tmpSeenPorts.filter(t => JSON.stringify(t) === JSON.stringify(portObject)).length == 0) {
        tmpSeenPorts.push(portObject)
      }

      setSeenPorts(tmpSeenPorts)

      // Add callsigns
      const callsignArray = []
      callsignArray.push(t.report.srce)
      callsignArray.push(t.report.dest)
      callsignArray.sort()

      if (tmpSeenL2Callsigns.filter(t => JSON.stringify(t) === JSON.stringify(callsignArray)).length == 0) {
        tmpSeenL2Callsigns.push(callsignArray)
      }

      setSeenL2Callsigns(tmpSeenL2Callsigns)

    })

    console.log('Seen NET/ROM Circuits', tmpSeenCcts)
    console.log('Seen Ports', tmpSeenPorts)
    console.log('Seen L2 Callsigns', tmpSeenL2Callsigns)
  } 

  const filterTraces = () => {

    // STEP 1 of 3
    findSeenCallsignsAndNetRom()

    // STEP 2 of 3
    // Filter traces based on selected L2 callsigns and/or NET/ROM circuits

    iteratingLocalFilter.current = traces

    if (selectedNetRomCircuits.length > 0) {
      console.log('selected netrom ccts')
      iteratingLocalFilter.current = iteratingLocalFilter.current.filter(t => {
        const validTrace = selectedNetRomCircuits.filter(c => {
          if (t.report.toCct && t.report.toCct == c.toCct) {
            return true
          } 
        })
        if (validTrace.length > 0) return true
        return false
      })

      console.log('Iterating Trace after NetRom Ccts', iteratingLocalFilter.current)
    } 

    if (selectedPorts.length > 0) {
      console.log('selected ports')
      iteratingLocalFilter.current = iteratingLocalFilter.current.filter(t => {
        const validTrace = selectedPorts.filter(p => {
          if (t.report.reportFrom == p.reportFrom && t.report.port == p.port) {
            return true
          } 
        })
        if (validTrace.length > 0) return true
        return false
      })

      console.log('Iterating Trace after ports', iteratingLocalFilter.current)
    } 

    if (selectedL2Callsigns.length > 0) {
      console.log('selected callsigns', selectedL2Callsigns)
      iteratingLocalFilter.current = iteratingLocalFilter.current.filter(t => {
        const validTrace = selectedL2Callsigns.filter(c => {
          if ((t.report.srce == c[0] && t.report.dest == c[1]) || (t.report.srce == c[1] && t.report.dest == c[0])){
            return true
          } 
        })
        if (validTrace.length > 0) return true
        return false
      })

      console.log('Iterating Trace after L2 Callsigns', iteratingLocalFilter.current)
    }     

    // STEP 3 of 3
    // Filter the overall traces array based on the selected options
    
    const localFilteredTraces = iteratingLocalFilter.current.filter(t => {
      if (showOnlyRoutingInfo && t.report.l3type != 'Routing info') return false
      if (showOnlyFRMR && t.report.l2Type != 'FRMR') return false
      if (suppressNetRom && t.report.ptcl == 'NET/ROM') return false
      if (suppressInp3 && t.report.type == 'INP3') return false
      if (suppressNodes && t.report.type == 'NODES') return false
      if (suppressUI && t.report.l2Type == 'UI') return false
      return true
    })

    setFilteredTraces(localFilteredTraces)
    
  }

  const darkTheme = createTheme({
    palette: {
      mode: 'light',
    },
  });

  const alertModal = () => {
    
    return (
      <Modal show={showAlert} onClick={() => setShowAlert(false)}>
        <Modal.Dialog>
            <Modal.Header closeButton>
              {showAlert}
            </Modal.Header>
        </Modal.Dialog>
      </Modal>
    )
  }

  const jsonModal = () => {
        
    return (
        <Modal 
          show={showJson}
        >
          <Modal.Dialog>
              <Modal.Header closeButton onClick={() => setShowJson(false)}>
              </Modal.Header>
              <Modal.Body>
                  <JSONPretty id="json-pretty" data={showJson}></JSONPretty>
              </Modal.Body>
          </Modal.Dialog>
        </Modal>
    )
  }

  const getTextExtract = () => {

    let textData = []
    filteredTraces.map(ft => {
      const t = ft.report
      const timestamp = (ft.report.time) ? new Date(ft.report.time*1000) : new Date(ft.timestamp)
      const ax25String = `<${t.l2Type} ${t.cr}${t.pf ? ` ${t.pf}` : ''}${'tseq' in t ? ` S${t.tseq}` : ''}${'rseq' in t ? ` R${t.rseq}` : ''}>`
      const netRomStringArray = []
      if (t.ptcl == 'NET/ROM' && t.l3dst != 'L3RTT') {
        netRomStringArray.push(`NET/ROM`)
        if ('fromCct' in t) netRomStringArray.push(`fromCct=${t.fromCct}`)
        if ('toCct' in t) netRomStringArray.push(`toCct=${t.toCct}`)
        if ('txSeq' in t) netRomStringArray.push(`S${t.txSeq}`)
        if ('rxSeq' in t) netRomStringArray.push(`R${t.rxSeq}`)
        if ('payLen' in t) netRomStringArray.push(`payLen=${t.payLen}`)
      }
      
      textData.push(`${timestamp.toLocaleDateString()} ${timestamp.toLocaleTimeString()} ${t.reportFrom} ${t.dirn == 'sent' ? 'TX' : 'RX'} Port=${t.port} ${t.srce}>${t.dest} ${ax25String} ${netRomStringArray.join(' ')}\n`)
    })

    const textExtractFile = new Blob([textData.join('')], { type: 'text/plain' });
    const url = URL.createObjectURL(textExtractFile);
    const link = document.createElement("a");
    link.download = `${traceReportFrom.split(',').join('_')}_from_${traceStart.format('YYYY_MM_DD_HH_mm_ss')}_to_${traceEnd.format('YYYY_MM_DD_HH_mm_ss')}.txt`;
    link.href = url;
    link.click();

  }

  const getJsonExtract = () => {

    const textExtractFile = new Blob([JSON.stringify(filteredTraces, null, 2)], { type: 'text/plain' });
    const url = URL.createObjectURL(textExtractFile);
    const link = document.createElement("a");
    link.download = `${traceReportFrom.split(',').join('_')}_from_${traceStart.format('YYYY_MM_DD_HH_mm_ss')}_to_${traceEnd.format('YYYY_MM_DD_HH_mm_ss')}.json`;
    link.href = url;
    link.click();

  }

  const traceFetchHandler = () => {

    if (traceStart.isAfter(traceEnd)) setShowAlert('Start Date must be earlier than End Date')

    const queryParams = new URLSearchParams();

    traceReportFrom.split(',').map(rf => {
      queryParams.append("reportFrom", rf)
    })

    queryParams.append("limit", env.API_PAGE_SIZE)
    queryParams.append("from", traceStart.format('YYYY-MM-DD[T]HH:mm:ss[Z]'))
    queryParams.append("to", traceEnd.format('YYYY-MM-DD[T]HH:mm:ss[Z]'))
    queryParams.append("includeCount", true)

    if (routingInfoOnly) {
      queryParams.append("l3type", "Routing info")
    }

    getTraces(queryParams)

  }

  const linkToClipboard = () => {
    
    navigator.clipboard.writeText(window.location.href)

    setShowAlert('Search link copied to clipboard')

  }

  return (
    <>
    { jsonModal() }
    { alertModal() }
    <ThemeProvider theme={darkTheme}>
      <Container fluid className='app-container'>
        <Row>
          <Col>
            <div style={{ margin: '0.5rem 0rem 0.7rem 0rem', display: 'flex', alignItems: 'center' }}>
              <Image src={appIcon} style={{ height: '4em' }} />
              <div style={{ margin: '0px 5px', width: '100%' }}>
                <pre style={{ overflow: 'hidden', fontSize: '1.8em', marginBottom: '0px', lineHeight: '1em' }}>Pac-Mon</pre>
                <pre style={{ marginLeft: '2px', marginBottom: '0px', whiteSpace: 'pre-wrap',  width: '100%'  }}><span style={{ display: 'inline-block' }}>Search, Filter and Analyse AX.25 Trace data</span><span style={{ display: 'inline-block', marginLeft: 'auto' }}></span></pre>
              </div>
              <hr />
            </div>
          </Col>
        </Row>
        <Row style={{ display: toggleApiSearch ? 'none' : 'flex' }}>
          <Col sm={3}>
            <TextField 
              label='Report(s) From' 
              size='small'
              fullWidth
              value={traceReportFrom}
              onChange={(e) => setTraceReportFrom(e.target.value)}
            />
          </Col>
          <Col sm={3}>
            <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale="en-gb">
              <DateTimePicker 
                sx={{ width: '100%' }}
                label="Trace Start"
                format="DD/MM/YYYY HH:mm:ss"
                slotProps={{ textField: { size: 'small' } }}
                value={traceStart}
                onChange={(newValue) => setTraceStart(newValue)}
                views={['year', 'day', 'hours', 'minutes', 'seconds' ]}
                ampm={false}
              />
            </LocalizationProvider>
          </Col>
          <Col sm={3}>
            <LocalizationProvider dateAdapter={AdapterMoment}>
              <DateTimePicker 
                sx={{ width: '100%' }}
                label="Trace End"
                format="DD/MM/YYYY HH:mm:ss"
                slotProps={{ textField: { size: 'small' } }}
                value={traceEnd}
                onChange={(newValue) => setTraceEnd(newValue)}
                views={['year', 'day', 'hours', 'minutes', 'seconds' ]}
                ampm={false}
              />
            </LocalizationProvider>
          </Col>
          <Col sm={3}>
            <Button style={{ width: '100%' }} onClick={() => traceFetchHandler()}>Fetch Data</Button>
          </Col>
        </Row>
        {/* <Row>
          <Col sm={3} style={{ display: 'flex', alignItems: 'center', marginTop: '0.5rem' }}>
              <Form.Check
                type="switch"
                label="Routing Info Only"
                checked={routingInfoOnly}
                onChange={(e) => setRoutingInfoOnly(e.target.checked)}
              />
          </Col>
        </Row> */}
        <hr style={{ margin: '0.5rem 0rem' }}/>
        { traces.length > 0 && <>
        <Row>
          <Col>
            <Badge 
              style={{ padding: '0.5em 0em', width: '100%', marginBottom: '0.5rem'}} 
              bg={donwloadedRecordCount < recordCount ? "danger" : "success"}
            >
              {donwloadedRecordCount == env.MAX_PERMITTED_DOWNLOAD_SIZE ? 'Maximum ' : null}{recordCount && `${donwloadedRecordCount.toLocaleString()} of ${recordCount.toLocaleString()} Available Traces Downloaded`}
              &nbsp;&nbsp;<span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => setToggleApiSearch(!toggleApiSearch)}>{toggleApiSearch ? 'Show' : 'Hide'} API Search</span>
            </Badge>
          </Col>
        </Row>
          <Row style={{ display: toggleFilters ? 'none' : 'flex' }}>
            <Col sm={4}>
              <Autocomplete
                multiple
                id="tags-outlined"
                options={seenNetRomCircuits}
                getOptionLabel={(c) => `${c.toCct}: ${c.l3src} <--> ${c.l3dst}`}
                defaultValue={selectedNetRomCircuits}
                onChange={(event, value) => setSelectedNetRomCircuits(value)}
                sx={{
                    "& .MuiOutlinedInput-root": {
                        paddingTop: 0, paddingBottom: 0, marginBottom: '6px'
                    },
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Seen NET/ROM Circuits"
                  />
                )}
                renderValue={(values, getItemProps) =>
                    values.map((option, index) => {
                      const { key, ...itemProps } = getItemProps({ index });
                      return (
                          <Chip
                              key={key}
                              label={`${option.toCct}: ${option.l3src} <--> ${option.l3dst}`}
                              {...itemProps}
                              sx={{ fontSize: "0.9em", borderRadius: '5px', color: 'white', backgroundColor: 'purple', height: 'auto', padding: '2px', '& .MuiChip-deleteIcon': { color: 'white' } }}
                          />
                      );
                    })
                }
              />
            </Col>
            <Col sm={4}>
              <Autocomplete
                multiple
                id="tags-outlined"
                options={seenPorts}
                getOptionLabel={(p) => `Port ${p.port} at ${p.reportFrom}`}
                defaultValue={selectedPorts}
                onChange={(event, value) => setSelectedPorts(value)}
                sx={{
                    "& .MuiOutlinedInput-root": {
                        paddingTop: 0, paddingBottom: 0, marginBottom: '6px'
                    },
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Seen Ports"
                  />
                )}
                renderValue={(values, getItemProps) =>
                    values.map((option, index) => {
                      const { key, ...itemProps } = getItemProps({ index });
                      return (
                          <Chip
                              key={key}
                              label={`Port ${option.port} at ${option.reportFrom}`}
                              {...itemProps}
                              sx={{ fontSize: "0.9em", borderRadius: '5px', color: 'white', backgroundColor: 'gray', height: 'auto', padding: '2px', '& .MuiChip-deleteIcon': { color: 'white' } }}
                          />
                      );
                    })
                }
              />
            </Col>
            <Col sm={4}>
              <Autocomplete
                multiple
                id="tags-outlined"
                options={seenL2Callsigns}
                getOptionLabel={(sc) => `${sc[0]} <--> ${sc[1]}`}
                defaultValue={selectedL2Callsigns}
                onChange={(event, value) => setSelectedL2Callsigns(value)}
                // defaultValue={[top100Films[0]]}
                sx={{
                    "& .MuiOutlinedInput-root": {
                        paddingTop: 0, paddingBottom: 0, marginBottom: '6px'
                    },
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Seen L2 Callsigns"
                  />
                )}
                renderValue={(values, getItemProps) =>
                    values.map((option, index) => {
                      const { key, ...itemProps } = getItemProps({ index });
                      return (
                          <Chip
                              key={key}
                              label={`${option[0]} <--> ${option[1]}}`}
                              {...itemProps}
                              sx={{ fontSize: "0.9em", borderRadius: '5px', color: 'white', backgroundColor: 'gray', height: 'auto', padding: '2px', marginTop: '0.5px', '& .MuiChip-deleteIcon': { color: 'white' } }}
                          />
                      );
                    })
                }
              />
            </Col>
          </Row>            
          <Row style={{ display: toggleFilters ? 'none' : 'flex' }}>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Suppress NODES"
                checked={suppressNodes}
                onChange={(e) => setSuppressNodes(e.target.checked)}
              />
            </Col>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Suppress UI"
                checked={suppressUI}
                onChange={(e) => setSuppressUI(e.target.checked)}
              />
            </Col>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Suppress NET/ROM"
                checked={suppressNetRom}
                onChange={(e) => setSuppressNetRom(e.target.checked)}
              />
            </Col>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Suppress INP3"
                checked={suppressInp3}
                onChange={(e) => setSuppressInp3(e.target.checked)}
              />
            </Col>
          </Row>            
          <Row style={{ display: toggleFilters ? 'none' : 'flex' }}>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Show L2 Counters"
                checked={showSequenceCounters}
                onChange={(e) => setShowSequenceCounters(e.target.checked)}
              />
            </Col>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Show Payload Length"
                checked={showPayLen}
                onChange={(e) => setShowPayLen(e.target.checked)}
              />
            </Col>
            <Col sm={3}>
              <Form.Check
                type="switch"
                label="Show NET/ROM Details"
                checked={showNetRomDetails}
                onChange={(e) => setShowNetRomDetails(e.target.checked)}
              />
            </Col>
            { filteredTraces.filter(t => t.report.l2Type == 'FRMR').length > 0 &&
              <Col sm={3}>
                <Form.Check
                  type="switch"
                  label="Show Only FRMR"
                  checked={showOnlyFRMR}
                  onChange={(e) => setShowOnlyFRMR(e.target.checked)}
                />
              </Col>
            }
          </Row>
          <Row>
            <Col>
                <Form.Check
                  type="switch"
                  label="Show Only Routing Info"
                  checked={showOnlyRoutingInfo}
                  onChange={(e) => setShowOnlyRoutingInfo(e.target.checked)}
                />            
            </Col>
          </Row>
          <Row>
            <Col>
              <Badge style={{ padding: '0.5em 0em', width: '100%', marginBottom: '0rem'}} bg={"secondary"}>
                {filteredTraces.length.toLocaleString()} Traces After Filtering
                &nbsp;<span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => setToggleFilters(!toggleFilters)}>{toggleFilters ? 'Show' : 'Hide'} Filters</span>
              </Badge>
            </Col>
          </Row>
          <hr style={{ margin: '0.5rem 0rem' }}/>
        </>
        }
        {
          <div style={{ display: 'flex', flex: 1, overflow: 'scroll', flexDirection: 'column' }}>
            {
              filteredTraces && filteredTraces.map(t => {
                if (routingInfoOnly) {
                  return null
                } else {
                  return <div className="traceContainer" onClick={() => setShowJson(t)}>
                    <Trace trace={t} showOnlyRoutingInfo={showOnlyRoutingInfo} showSequenceCounters={showSequenceCounters} showPayLen={showPayLen} showNetRomDetails={showNetRomDetails}/>
                  </div>
                }
              })
            }
          </div>
        }
        <Row style={{ margin: '0.5em 0em 0.3em 0em', backgroundColor: 'lightgray' }}>
          <Col sm={3} style={{ textAlign: 'center' }}>
            <span>Version {env.VERSION}</span>
          </Col>
          { filteredTraces.length > 0 &&
            <>
              <Col sm={3} style={{ textAlign: 'center' }}>
                <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => linkToClipboard()}>Get Search Link</span>
              </Col>
              <Col sm={3} style={{ textAlign: 'center' }}>
                <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => getTextExtract()}>Get Text Extract</span>
              </Col>
              <Col sm={3} style={{ textAlign: 'center' }}>
                <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => getJsonExtract()}>Get JSON Extract</span>
              </Col>
            </>
          }
        </Row>
      </Container>
    </ThemeProvider>
  </>
  )
}

export default App
