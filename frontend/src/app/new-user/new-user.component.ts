import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
import { APIService } from '../api.service';
import { Router } from '@angular/router';
import { Md5 } from 'ts-md5'

declare var jQuery : any;

@Component({
  selector: 'app-new-user',
  templateUrl: './new-user.component.html',
  styleUrls: ['./new-user.component.css']
})
export class NewUserComponent implements OnInit {

  @ViewChild('newUserModal') newUserModal : ElementRef;

  constructor(public api : APIService, private router : Router) { }

  ngOnInit() {
  }

  createUser(name: string, passwordClear: string) {
    let password = Md5.hashStr(passwordClear);
    this.api.createUser(name, password).then(
      data => {
        jQuery(this.newUserModal.nativeElement).one('hidden.bs.modal', _ => {
          this.router.navigate(['user', data]);
        })
        jQuery(this.newUserModal.nativeElement).modal('toggle');
      }, error => {
      }
    )
  }

}
