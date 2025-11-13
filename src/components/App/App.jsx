// React & Pac-Mon
import { useState, useContext, useEffect, useRef } from 'react'
import { ApiContext } from '../../contexts/ApiContext'
import Trace from '../Trace/Trace';
import * as env from '../../env/env'
import './App.css'
import appIcon from '../../images/appIcon1.png'
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
      traces,
      recordCount,
      donwloadedRecordCount
  } = useContext(ApiContext);

  // API Filter States
  const [showJson, setShowJson] = useState(null)
  const [traceReportFrom, setTraceReportFrom] = useState('MB7NPW,GB7NBH');
  const [traceStart, setTraceStart] = useState(moment().subtract(15,'minutes'));
  const [traceEnd, setTraceEnd] = useState(moment());
  
  // Local Filter States
  const [suppressNetRom, setSuppressNetRom] = useState(false)
  const [suppressInp3, setSuppressInp3] = useState(false)
  const [suppressUI, setSuppressUI] = useState(true)
  const [suppressNodes, setSuppressNodes] = useState(true)
  const [showSequenceCounters, setShowSequenceCounters] = useState(false)
  const [showNetRomCircuits, setShowNetRomCircuits] = useState(false)
  const [showPayLen, setShowPayLen] = useState(false)

  // Data States
  const [filteredTraces, setFilteredTraces] = useState([]);
  const [seenNetRomCircuits, setSeenNetRomCircuits] = useState([]);
  const [seenCallsigns, setSeenCallsigns] = useState([]);
  
  // Re-run the filter if any of the local filter states change
  useEffect(() => {
    filterTraces()
  }, [traces, suppressNetRom, suppressInp3, suppressUI, suppressNodes]);

  const filterTraces = () => {
    
    // Filter the overall traces array based on the selected options
    const localFilteredTraces = traces.filter(t => {
      if (suppressNetRom && t.report.ptcl == 'NET/ROM') return false
      if (suppressInp3 && t.report.l3type == 'INP3') return false
      if (suppressNodes && t.report.type == 'NODES') return false
      if (suppressUI && t.report.l2Type == 'UI') return false

      //if ((t.report.srce != tmpArray[0] || t.report.dest != tmpArray[1]) && (t.report.srce != tmpArray[1] || t.report.dest != tmpArray[0])) return false

      return true
    })

    // Iterate the filtered traces to extract source and destination callsigns 

    const tmpSeenCcts = []
    const tmpSeenCallsigns = []

    localFilteredTraces.map(t => {
      
      if (t.report.ptcl == 'NET/ROM' && t.report.toCct) {
        // Add NET/ROM circuits
        const circuitObject = {}
        circuitObject.toCct = t.report.toCct
        circuitObject.l3src = t.report.l3src
        circuitObject.l3dst = t.report.l3dst

        if (tmpSeenCcts.filter(c => JSON.stringify(c) === JSON.stringify(circuitObject)).length == 0) {
          tmpSeenCcts.push(circuitObject)
        }        

      }

      // Add callsigns
      const callsignArray = []
      callsignArray.push(t.report.srce)
      callsignArray.push(t.report.dest)

      callsignArray.sort()

      if (tmpSeenCallsigns.filter(t => JSON.stringify(t) === JSON.stringify(callsignArray)).length == 0) {
        tmpSeenCallsigns.push(callsignArray)
      }

    })

    console.log('Seen NET/ROM Circuits', tmpSeenCcts)
    console.log('Seen L2 Callsigns', tmpSeenCallsigns)

    setFilteredTraces(localFilteredTraces)
    setSeenNetRomCircuits(tmpSeenCcts.sort((a,b) => a.toCct - b.toCct))
    setSeenCallsigns(tmpSeenCallsigns)
    
  }

  const darkTheme = createTheme({
    palette: {
      mode: 'light',
    },
  });

  const jsonModal = () => {
        
    return (
      <Modal show={showJson}>
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

  const traceFetchHandler = () => {

    const queryParams = new URLSearchParams();

    traceReportFrom.split(',').map(rf => {
      queryParams.append("reportFrom", rf)
    })

    queryParams.append("limit", env.API_PAGE_SIZE)
    queryParams.append("from", traceStart.format('YYYY-MM-DD[T]HH:mm:[00Z]'))
    queryParams.append("to", traceEnd.format('YYYY-MM-DD[T]HH:mm:[00Z]'))
    queryParams.append("includeCount", true)

    getTraces(queryParams)

  }
  return (
    <>
    { jsonModal() }
    <ThemeProvider theme={darkTheme}>
      <Container fluid className='app-container'>
        <Row>
          <Col>
            <div style={{ margin: '0.5rem 0rem 0.7rem 0rem', display: 'flex', alignItems: 'center' }}>
              <Image src={appIcon} style={{ height: '4em' }} />
              <div style={{ fontSize: '2em' }}>
                <pre style={{margin: 'auto 5px' }}>Pac-Mon</pre>
              </div>
              <hr />
            </div>
          </Col>
        </Row>
        <Row>
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
                format="DD/MM/YYYY HH:mm"
                slotProps={{ textField: { size: 'small' } }}
                defaultValue={traceStart}
                onChange={(newValue) => setTraceStart(newValue)}
                views={['year', 'day', 'hours', 'minutes' ]}
                ampm={false}
              />
            </LocalizationProvider>
          </Col>
          <Col sm={3}>
            <LocalizationProvider dateAdapter={AdapterMoment}>
              <DateTimePicker 
                sx={{ width: '100%' }}
                label="Trace End"
                format="DD/MM/YYYY HH:mm"
                slotProps={{ textField: { size: 'small' } }}
                value={traceEnd}
                onChange={(newValue) => setTraceEnd(newValue)}
                views={['year', 'day', 'hours', 'minutes' ]}
                ampm={false}
              />
            </LocalizationProvider>
          </Col>
          <Col sm={3}>
            <Button style={{ width: '100%' }} onClick={() => traceFetchHandler()}>Fetch Data</Button>
          </Col>
        </Row>
        <hr style={{ margin: '0.5rem 0rem' }}/>
        { traces.length > 0 && <>
        <Row>
          <Col>
            <Badge style={{ padding: '0.5em 0em', width: '100%', marginBottom: '0.5rem'}} bg={donwloadedRecordCount < recordCount ? "danger" : "success"}>{recordCount && `${donwloadedRecordCount.toLocaleString()} of ${recordCount.toLocaleString()} Traces Returned`}</Badge>
            {/* <ProgressBar variant="success" now={Math.round(Number(donwloadedRecordCount/recordCount)*100)} label={`${donwloadedRecordCount.toLocaleString()} of ${recordCount.toLocaleString()} Records Returned`} />; */}
          </Col>
        </Row>
          <Row>
            <Col sm={6}>
              <Autocomplete
                multiple
                id="tags-outlined"
                options={seenNetRomCircuits}
                getOptionLabel={(c) => `${c.toCct}: ${c.l3src} <--> ${c.l3dst}`}
                // defaultValue={[top100Films[0]]}
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
            <Col sm={6}>
              <Autocomplete
                multiple
                id="tags-outlined"
                options={seenCallsigns}
                getOptionLabel={(sc) => `${sc[0]} <--> ${sc[1]}}`}
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
            <Row>
                <Col>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <Form.Check
                      defaultChecked={suppressNodes}
                      type="switch"
                      label="Suppress NODES"
                      onChange={(e) => setSuppressNodes(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      defaultChecked={suppressUI}
                      type="switch"
                      label="Suppress UI"
                      onChange={(e) => setSuppressUI(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      type="switch"
                      label="Suppress NET/ROM"
                      onChange={(e) => setSuppressNetRom(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      type="switch"
                      label="Suppress INP3"
                      onChange={(e) => setSuppressInp3(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      type="switch"
                      label="Show L2 Sequence Counters"
                      onChange={(e) => setShowSequenceCounters(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      type="switch"
                      label="Show Payload Length"
                      onChange={(e) => setShowPayLen(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      type="switch"
                      label="Show NET/ROM Circuits"
                      onChange={(e) => setShowNetRomCircuits(e.target.checked)}
                    />
                    <div style={{ marginLeft: 'auto' }}>Local Count: {filteredTraces.length}</div>
                  </div>
                </Col>
            </Row>
            <hr style={{ margin: '0.5rem 0rem' }}/>
          </>
        }
        {
          <Row>
            {
              filteredTraces && filteredTraces.map(t => {
                return <div className="traceContainer" onClick={() => setShowJson(t)}>
                    <Trace trace={t} showSequenceCounters={showSequenceCounters} showPayLen={showPayLen} showNetRomCircuits={showNetRomCircuits}/>
                  </div>
              })
            }
          </Row>
        }
      </Container>
    </ThemeProvider>
  </>
  )
}

export default App
