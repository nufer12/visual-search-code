import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-generic-list-scaling',
  templateUrl: './generic-list-scaling.component.html',
  styleUrls: ['./generic-list-scaling.component.scss']
})
export class GenericListScalingComponent implements OnInit {

  @Input() bootstrapScale : number = 3;
  @Output() rescaled = new EventEmitter<number>();

  constructor() { }

  ngOnInit() {
  }

  sendNewScale() {
    this.rescaled.emit(this.bootstrapScale);
    setTimeout(_ => {
      window.dispatchEvent(new Event('resize'));
    }, 250);
    
  }

}
