import * as diagram from './diagram-creation'
import {dataUpdate, handleDeleteBtnClick} from './base-setup'
import $ from 'jquery';

import '../css/index.css';
import '../css/diagram.css';

import {handleSaveSettingsBtnClick} from "./settings-change";

$('#delete_btn').click(handleDeleteBtnClick(diagram.refresh));

window.setInterval(dataUpdate(diagram.refresh), 100000);

$('#save_settings_btn').click(handleSaveSettingsBtnClick(diagram.refresh));
