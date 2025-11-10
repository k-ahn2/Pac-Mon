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

const Tag = styled.span`
    padding: 0em 0.3em;
    margin: 0em 0.1em;
    border-radius: 0.2em;
`

export const Trace = (props) => {

    const trace = props.trace.report
    
    useEffect(() => {
        
    }, [props]);

    const callsigns = `${trace.srce} to ${trace.dest}`
    const headers = `<${trace.l2Type} ${trace.cr}>`
    const timestamp = new Date(props.trace.timestamp)

    const generateTags = () => {
        const tags = []
        if (trace.l2Type == 'C') tags.push(<Tag style={{ backgroundColor: 'green', color: 'white' }}>CONN</Tag>)
        if (trace.l2Type == 'D') tags.push(<Tag style={{ backgroundColor: 'red', color: 'white' }}>DISC</Tag>)
        if (trace.l2Type == 'UA') tags.push(<Tag style={{ backgroundColor: 'gray', color: 'white' }}>ACK</Tag>)
        if (trace.ptcl == 'NET/ROM') tags.push(<Tag style={{ backgroundColor: 'purple', color: 'white' }}>NET/ROM</Tag>)
        
        if (trace.l4type && (trace.l4type == 'CONN REQ' || trace.l4type == 'CONN ACK')) { 
            tags.push(<Tag style={{ backgroundColor: 'green', color: 'white' }}>{ trace.l4type }</Tag>)
        } else if (trace.l4type && (trace.l4type == 'DISC REQ' || trace.l4type == 'DISC ACK')) { 
            tags.push(<Tag style={{ backgroundColor: 'red', color: 'white' }}>{ trace.l4type }</Tag>)
        } else if (trace.l4type) {
            tags.push(<Tag style={{ backgroundColor: 'gray', color: 'white' }}>{ trace.l4type }</Tag>)
        } 

        if (trace.l3dst == 'L3RTT') tags.push(<Tag style={{ backgroundColor: 'gray', color: 'white' }}>INP3 RTT</Tag>)

        if (trace.type == 'NODES') tags.push(<Tag style={{ backgroundColor: 'gray', color: 'white' }}>NODES</Tag>)

        if (props.showPayLen && trace.payLen) tags.push(<Tag style={{ backgroundColor: 'gray', color: 'white' }}>plen={trace.payLen}</Tag>)
        if (props.showPayLen && trace.ilen) tags.push(<Tag style={{ backgroundColor: 'gray', color: 'white' }}>ilen={trace.ilen}</Tag>)


        return tags
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
                            <Tag style={{ backgroundColor: 'green', color: 'white' }}>RX</Tag> : 
                            <Tag style={{ backgroundColor: 'red', color: 'white' }}>TX</Tag>
                        }
                    </TraceData>
                    <TraceData>
                        Port {trace.port}:
                    </TraceData>
                    { props.showSequenceCounters && 
                    <TraceData>
                        { trace.tseq >= 0 && <Tag style={{ backgroundColor: 'red', color: 'white' }}>{trace.tseq}</Tag>}
                        { trace.rseq >= 0 && <Tag style={{ backgroundColor: 'green', color: 'white' }}>{trace.rseq}</Tag>}
                    </TraceData>                    
                    }
                    <TraceData>
                        {callsigns}
                    </TraceData>
                    <TraceData>
                        {headers}
                    </TraceData>
                    <TraceData>
                        { generateTags() }
                    </TraceData>                    
                </TraceRow>
            </TraceComponentWrapper>
        </>
    )

}

export default Trace;