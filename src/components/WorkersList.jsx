import { styled } from '@mui/material/styles';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell, { tableCellClasses } from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';

import { useSelector } from "react-redux";

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.${tableCellClasses.head}`]: {
    backgroundColor: theme.palette.common.black,
    color: theme.palette.common.white,
  },
  [`&.${tableCellClasses.body}`]: {
    fontSize: 14,
  },
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  '&:nth-of-type(odd)': {
    backgroundColor: theme.palette.action.hover,
  },
  // hide last border
  '&:last-child td, &:last-child th': {
    border: 0,
  },
}));


export default function WorkersList() {
  const slaves = useSelector(state => state.domain.slaves)
  console.log("SLAVES")
  console.log(slaves, Object.keys(slaves))
  Object.keys(slaves).forEach(key => {
    console.log(slaves[key], slaves[key].device)
  })

  const finished = useSelector(state => state.domain.finished)

  return (finished &&
    <TableContainer style={{marginBottom: '10px'}} component={Paper}>
      <Table sx={{ minWidth: 700 }} aria-label="customized table">
        <TableHead>
          <TableRow>
            <StyledTableCell align="center">Slave ID</StyledTableCell>
            <StyledTableCell align="center">Device</StyledTableCell>
            <StyledTableCell align="center">Links found</StyledTableCell>
            <StyledTableCell align="center">Total bytes mb</StyledTableCell>
            <StyledTableCell align="center">Pages processed</StyledTableCell>
            <StyledTableCell align="center">AVG page size (kb)</StyledTableCell>
            <StyledTableCell align="center">AVG processing time</StyledTableCell>
            <StyledTableCell align="center">Errors</StyledTableCell>
            <StyledTableCell align="center">Timeout errors</StyledTableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {Object.keys(slaves).map((slave_id) => {
            console.log("BABABAB")
            return (
            <StyledTableRow key={slave_id}>
              <StyledTableCell align="center" component="th" scope="row">
                {slave_id}
              </StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].device}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].links_found}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].total_bytes_mb}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].pages_processed}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].avg_page_size_kb}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].avg_processing_time}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].errors}</StyledTableCell>
              <StyledTableCell align="center">{slaves[slave_id].timeout_errors}</StyledTableCell>
            </StyledTableRow>
          )})}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
