import styled from "styled-components";

const TraceComponentWrapper = styled.div`
  display: flex;
  flex-direction: column;
  padding: 0.1em 0em;
`;

const TraceRow = styled.div`
    display: flex;
    flex: 1;
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
    color: white;
    background-color: gray;
`

export const Trace = (props) => {

    const l2TypesThatSuppressTseq = ['RR', 'RNR', 'REJ', 'SREJ']

    const trace = props.trace.report
    const timestamp = (props.trace.report.time) ? new Date(props.trace.report.time*1000) : new Date(props.trace.timestamp)

    const generateTags = () => {
        const tags = []
        
        if (trace.l2Type == 'FRMR') tags.push(<Tag style={{ backgroundColor: 'red' }}>FRAME REJECT</Tag>)
        if (trace.l2Type == 'C') tags.push(<Tag style={{ backgroundColor: 'green' }}>CONN</Tag>)
        if (trace.l2Type == 'D') tags.push(<Tag style={{ backgroundColor: 'red' }}>DISC</Tag>)
        if (trace.l2Type == 'UA') tags.push(<Tag>ACK</Tag>)
        if (trace.ptcl == 'NET/ROM') tags.push(<Tag style={{ backgroundColor: 'purple' }}>NET/ROM</Tag>)
        if (trace.srcUser) tags.push(<Tag style={{ backgroundColor: 'green' }}>{trace.srcUser}</Tag>)
        
        if (trace.l4type && (trace.l4type == 'CONN REQ' || trace.l4type == 'CONN ACK')) { 
            tags.push(<Tag style={{ backgroundColor: 'green' }}>{ trace.l4type }</Tag>)
        } else if (trace.l4type && (trace.l4type == 'DISC REQ' || trace.l4type == 'DISC ACK')) { 
            tags.push(<Tag style={{ backgroundColor: 'red' }}>{ trace.l4type }</Tag>)
        } else if (trace.l4type) {
            tags.push(<Tag>{ trace.l4type }</Tag>)
        } 

        if (trace.l3dst == 'L3RTT') tags.push(<Tag>INP3 RTT</Tag>)
        if (trace.type == 'NODES') tags.push(<Tag>NODES</Tag>)
        
        if (trace.type == 'INP3' && trace.l3type == 'Routing info') tags.push(<Tag>INP3 Routing Info</Tag>)
        if (props.showNetRomDetails && 'fromCct' in trace) tags.push(<Tag style={{ backgroundColor: 'purple' }}>{trace.fromCct}</Tag>)
        if (props.showNetRomDetails && 'toCct' in trace && trace.l3dst != 'L3RTT') tags.push(<Tag style={{ backgroundColor: 'purple' }}>{trace.toCct}</Tag>)
        if (props.showNetRomDetails && 'txSeq' in trace && trace.l3dst != 'L3RTT') tags.push(<Tag style={{ backgroundColor: 'red' }}>S{trace.txSeq}</Tag>)
        if (props.showNetRomDetails && 'rxSeq' in trace && trace.l3dst != 'L3RTT') tags.push(<Tag style={{ backgroundColor: 'green' }}>R{trace.rxSeq}</Tag>)

        if (props.showPayLen && trace.payLen) tags.push(<Tag>plen={trace.payLen}</Tag>)
        // if (props.showPayLen && trace.ilen) tags.push(<Tag>ilen={trace.ilen}</Tag>)

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
                            <Tag style={{ backgroundColor: 'green' }}>RX</Tag> : 
                            <Tag style={{ backgroundColor: 'red' }}>TX</Tag>
                        }
                    </TraceData>
                    <TraceData>
                        Port {trace.port}:
                    </TraceData>
                    { props.showSequenceCounters && 
                    <TraceData>
                        { trace.tseq >= 0 && <Tag style={{ backgroundColor: 'red' }}>S{trace.tseq}</Tag>}
                        { trace.rseq >= 0 && <Tag style={{ backgroundColor: 'green' }}>R{trace.rseq}</Tag>}
                    </TraceData>                    
                    }
                    <TraceData>
                        {`${trace.srce} to ${trace.dest}`}
                    </TraceData>
                    <TraceData>
                        {`<${trace.l2Type} ${trace.cr}${trace.pf ? ` ${trace.pf}` : ''}${'tseq' in trace ? ` S${trace.tseq}` : ''}${'rseq' in trace ? ` R${trace.rseq}` : ''}>`}
                    </TraceData>
                    <TraceData>
                        { generateTags() }
                    </TraceData>                    
                </TraceRow>
                {
                    trace.l3type == 'Routing info' && props.showOnlyRoutingInfo &&
                    trace.nodes.map((route, index) => (
                        <TraceRow key={index} style={{ margin: '0.1em 2em' }}>
                            <TraceData>
                                <Tag>{route.call}</Tag> <Tag style={{ backgroundColor: 'green' }}>Hops={route.hops}</Tag> <Tag style={{ backgroundColor: 'green' }}>{route.tt/100}s</Tag>
                            </TraceData>
                        </TraceRow>
                    ))
                }
            </TraceComponentWrapper>
        </>
    )

}

export default Trace;