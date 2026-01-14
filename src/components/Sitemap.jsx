import * as React from 'react';
import ListSubheader from '@mui/material/ListSubheader';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Collapse from '@mui/material/Collapse';
import InboxIcon from '@mui/icons-material/MoveToInbox';
import DraftsIcon from '@mui/icons-material/Drafts';
import SendIcon from '@mui/icons-material/Send';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import StarBorder from '@mui/icons-material/StarBorder';

import PropTypes from 'prop-types';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';

import { useSelector } from "react-redux";
import { padding } from '@mui/system';

function CustomTabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

CustomTabPanel.propTypes = {
  children: PropTypes.node,
  index: PropTypes.number.isRequired,
  value: PropTypes.number.isRequired,
};

function a11yProps(index) {
  return {
    id: `simple-tab-${index}`,
    'aria-controls': `simple-tabpanel-${index}`,
  };
}

export default function Sitemap() {
  const [value, setValue] = React.useState(0);

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  const finished = useSelector(state => state.domain.finished)

  const ulinks = useSelector(state => state.domain.ulinks)
  let js_list, image_list
  if (ulinks['internal_links']) {
    js_list = ulinks['internal_links']['by_type']['javascript']
    image_list = ulinks['internal_links']['by_type']['image']
  }
  console.log(js_list, image_list)

  return finished && (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={value} onChange={handleChange} aria-label="basic tabs example">
          {js_list && <Tab label="JavaScript" {...a11yProps(0)} /> }
          {image_list && <Tab label="Images" {...a11yProps(1)} /> }
          {/* <Tab label="Item Three" {...a11yProps(2)} /> */}
        </Tabs>
      </Box>
      { js_list && Object.keys(js_list).map(js_key => 
      <CustomTabPanel style={{height: '1.7rem'}} value={value} index={0}>
        {js_list[js_key]}
      </CustomTabPanel>) }
       { image_list && Object.keys(image_list).map(image_key => 
      <CustomTabPanel style={{height: '1.7rem'}} value={value} index={1}>
        {image_list[image_key]}
      </CustomTabPanel>) }
    </Box>
  )

  
}



  // <List 
  //   sx={{ width: '100%', bgcolor: 'background.paper', marginTop: '10px' }}
  //   component="nav"
  //   aria-labelledby="nested-list-subheader"
  //   subheader={
  //     <ListSubheader component="div" id="nested-list-subheader-js">
  //       Internal links
  //     </ListSubheader>
  //   }
  // >
  //   {/* Условная отрисовка для JavaScript раздела */}
  //   {js_list && (
  //     <>
  //       <ListItemButton onClick={handleClickJS}>
  //         <ListItemText primary="JavaScript" />
  //         {openJS ? <ExpandLess /> : <ExpandMore />}
  //       </ListItemButton>
  //       <Collapse in={openJS} timeout="auto" unmountOnExit>
  //         <List component="div" disablePadding>
  //           {Object.keys(js_list).map(js_item => (
  //             <ListItemButton key={js_item} sx={{ pl: 4 }}>
  //               <ListItemText primary={js_list[js_item]} />
  //             </ListItemButton>
  //           ))}
  //         </List>
  //       </Collapse>
  //     </>
  //   )}
    
  //   {/* Условная отрисовка для Image раздела */}
  //   {image_list && (
  //     <>
  //       <ListItemButton onClick={handleClickImage}>
  //         <ListItemText primary="Image" />
  //         {openImage ? <ExpandLess /> : <ExpandMore />}
  //       </ListItemButton>
  //       <Collapse in={openImage} timeout="auto" unmountOnExit>
  //         <List component="div" disablePadding>
  //           {Object.keys(image_list).map(item => (
  //             <ListItemButton key={item} sx={{ pl: 4 }}>
  //               <ListItemText primary={image_list[item]} />
  //             </ListItemButton>
  //           ))}
  //         </List>
  //       </Collapse>
  //     </>
  //   )}
  // </List>