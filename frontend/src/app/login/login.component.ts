import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { APIService } from '../api.service';
import { ManagedSubs } from '../util/managed-subs';

declare var jQuery : any;

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent extends ManagedSubs implements OnInit {

  @ViewChild('theLoginModal') theLoginModal : ElementRef;

  public failedAttempt : boolean = false;

  constructor(public api : APIService) {
    super();
  }

  ngOnInit() {
    this.manageSub('isAuth', this.api.isAuthenticated.subscribe(isAuth => {
      if(isAuth) {
        jQuery(this.theLoginModal.nativeElement).modal('hide');
        this.failedAttempt = false;
      } else {
        if(jQuery(this.theLoginModal.nativeElement).is(':visible')) {
          this.failedAttempt = true;
        } else {
          jQuery(this.theLoginModal.nativeElement).modal('show');
        }
      }
    }))
  }

}
