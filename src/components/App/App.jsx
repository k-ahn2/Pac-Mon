import { useState, useContext, useEffect, useRef } from 'react'
import { ApiContext } from '../../contexts/ApiContext'
import moment from 'moment';
import './App.css'
import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';
import 'bootstrap/dist/css/bootstrap.min.css';
import Trace from '../Trace/Trace';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { Col, Row } from 'react-bootstrap';
import styled from "styled-components";
import { ThemeProvider, createTheme } from '@mui/material/styles';
import TextField from '@mui/material/TextField';
import 'moment/locale/en-gb';
import Image from 'react-bootstrap/Image';
import appIcon from '../../images/appIcon1.png'
import Badge from 'react-bootstrap/Badge';
import { Form, Modal } from 'react-bootstrap';
import JSONPretty from 'react-json-pretty';
import * as env from '../../env/env'
import ProgressBar from 'react-bootstrap/ProgressBar';

function App() {
  
  const { 
      getTraces,
      traces,
      recordCount,
      donwloadedRecordCount
  } = useContext(ApiContext);

  const [showJsonModal, setShowJsonModal] = useState(null)
  const [traceReportFrom, setTraceReportFrom] = useState('MB7NPW,GB7NBH');
  const [traceStart, setTraceStart] = useState(moment().subtract(1,'hour'));
  const [traceEnd, setTraceEnd] = useState(moment().subtract(50,'minutes'));
  const [filteredTraces, setFilteredTraces] = useState([]);

  // Local Filter States
  const [suppressNetRom, setSuppressNetRom] = useState(false)
  const [suppressInp3, setSuppressInp3] = useState(false)
  const [suppressL2, setSuppressL2] = useState(false)
  const [suppressUI, setSuppressUI] = useState(false)
  const [suppressNodes, setSuppressNodes] = useState(true)
  const [showSequenceCounters, setShowSequenceCounters] = useState(false)

  useEffect(() => {
    console.log(traceReportFrom)
  }, [traceReportFrom]);

  useEffect(() => {
    filterTraces()
  }, [traces, suppressNetRom, suppressInp3, suppressL2, suppressUI, suppressNodes]);

  const filterTraces = () => {
      const localFilteredTraces = traces.filter(t => {
        if (suppressNetRom && t.report.ptcl == 'NET/ROM') return false
        if (suppressInp3 && t.report.l3type == 'INP3') return false
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

  const jsonModal = (trace) => {
        
    return (
      <Modal show={showJsonModal}>
        <Modal.Dialog>
            <Modal.Header closeButton onClick={() => setShowJsonModal(false)}>
            </Modal.Header>
            <Modal.Body>
                <JSONPretty id="json-pretty" data={showJsonModal}></JSONPretty>
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
        <Row>
          <Col>
            <Badge style={{ padding: '0.5em 0em', width: '100%', marginTop: '0.5rem'}} bg={donwloadedRecordCount < recordCount ? "danger" : "success"}>{recordCount && `${donwloadedRecordCount.toLocaleString()} of ${recordCount.toLocaleString()} Records Returned`}</Badge>
            {/* <ProgressBar variant="success" now={Math.round(Number(donwloadedRecordCount/recordCount)*100)} label={`${donwloadedRecordCount.toLocaleString()} of ${recordCount.toLocaleString()} Records Returned`} />; */}
          </Col>
        </Row>
        <hr style={{ margin: '0.5rem 0rem' }}/>
        { traces.length > 0 && <>
            <Row>
                <Col>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
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
                      defaultChecked={true}
                      type="switch"
                      label="Suppress NODES"
                      onChange={(e) => setSuppressNodes(e.target.checked)}
                    />
                    &nbsp;&nbsp;
                    <Form.Check
                      type="switch"
                      label="Show Sequence Counters"
                      onChange={(e) => setShowSequenceCounters(e.target.checked)}
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
                return <div className="traceContainer" onClick={() => setShowJsonModal(t)}>
                    <Trace trace={t} showSequenceCounters={showSequenceCounters}/>
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
