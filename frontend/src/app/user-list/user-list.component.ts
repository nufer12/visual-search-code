import { Component, OnInit } from '@angular/core';
import { GenericList } from '../util/generic-list';
import { APIService } from '../api.service';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.component.html',
  styleUrls: ['./user-list.component.scss']
})
export class UserListComponent extends GenericList implements OnInit {

  constructor(public api : APIService) {
    super();
  }

  ngOnInit() {
  }

}
