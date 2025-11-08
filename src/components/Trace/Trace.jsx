import { useEffect, useState } from "react";
import styled from "styled-components";

const TraceComponentWrapper = styled.div`
  display: flex;
  padding: 0.1em 0em;
`;

const TraceRow = styled.div`
    display: flex;
    flex-direction: row;
    font-family: Courier, monospace, 'Courier New';
`

const TraceData = styled.div`
    display: flex;
    padding: 0.05em 0em 0em 0.2em;
`

export const Trace = (props) => {

    const trace = props.trace.report
    
    useEffect(() => {
        
    }, [props]);

    const callsigns = `${trace.srce} to ${trace.dest}`
    const headers = `<${trace.l2Type} ${trace.cr}>`
    const timestamp = new Date(props.trace.timestamp)

    const traceType = () => {
        if (trace.ptcl == 'NET/ROM') {
            return <span style={{ padding: '0px 3px', backgroundColor: 'purple', color: 'white' }}>NET/ROM</span>
        }
    }

    return (
        <>
            <TraceComponentWrapper>
                <TraceRow>
                    <TraceData onClick={() => setShowJsonModal(true)}>
                        {timestamp.toLocaleTimeString()}
                    </TraceData>
                    <TraceData>
                        {trace.reportFrom}
                    </TraceData>
                    <TraceData>
                        {trace.dirn == 'rcvd' ? 
                            <span style={{ backgroundColor: 'green', color: 'white', padding: '0px 3px', margin: '0px 3px' }}>RX</span> : 
                            <span style={{ backgroundColor: 'red', color: 'white', padding: '0px 3px', margin: '0px 3px'}}>TX</span>
                        }
                    </TraceData>
                    <TraceData>
                        Port {trace.port}:
                    </TraceData>
                    <TraceData>
                        {callsigns}
                    </TraceData>
                    { trace.ptcl == 'NET/ROM' && <TraceData>
                        {traceType()}
                    </TraceData> }
                    <TraceData>
                        {headers}
                    </TraceData>
                    <TraceData>
                        { trace.tseq >= 0 && <span>tseq={trace.tseq}</span>}&nbsp;
                        { trace.rseq >= 0 && <span>rseq={trace.rseq}</span>}&nbsp;
                        { trace.l4type && <span>{trace.l4type}</span>}
                    </TraceData>
                </TraceRow>
            </TraceComponentWrapper>
        </>
    )

}

export default Trace;